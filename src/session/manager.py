from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from urllib.parse import parse_qs, urlparse

import httpx

from src.config import Settings
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class SessionExpired(Exception):
    pass


class SessionManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url: str = ""
        self.secure_hash: str = ""
        self.server_id: str = ""
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(1)
        self._last_request_at: float = 0
        self._on_session_expired: list = []
        self._connected = False
        self._game_host: str = ""

    @property
    def connected(self) -> bool:
        return self._connected and bool(self.secure_hash)

    async def inject_from_url(self, game_url: str, cookies: dict[str, str] | None = None) -> bool:
        parsed = urlparse(game_url)
        self._game_host = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/', 1)[0]}/"
        self.server_id = parsed.netloc.split(".")[0] if "." in parsed.netloc else parsed.netloc

        qs = parse_qs(parsed.query)
        sh = qs.get("sh", [None])[0]
        if sh:
            self.secure_hash = sh

        cookie_jar = httpx.Cookies()
        if cookies:
            for k, v in cookies.items():
                cookie_jar.set(k, v, domain=parsed.netloc)

        if self._client:
            await self._client.aclose()

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=cookie_jar,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": game_url,
            },
            follow_redirects=False,
            timeout=30.0,
        )

        try:
            html = await self._request_raw("GET", "index.php", params={"mod": "overview", "sh": self.secure_hash})
            if html is None:
                logger.warning("Session expired on first request — cookies are required")
                self._connected = False
                return False
            new_sh = GameParser.parse_secure_hash(html)
            if new_sh:
                self.secure_hash = new_sh
            self._connected = True
            logger.info("Session established for server %s", self.server_id)
            return True
        except SessionExpired:
            logger.warning("Session expired on first request — cookies are required")
            self._connected = False
            return False
        except Exception:
            logger.exception("Failed to validate session")
            self._connected = False
            return False

    async def get(self, path: str, params: dict | None = None) -> str:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, params: dict | None = None, data: dict | None = None) -> str:
        return await self._request("POST", path, params=params, data=data)

    async def _request_raw(self, method: str, path: str, **kwargs) -> str | None:
        """Low-level request. Returns HTML or None if session expired (302 redirect away)."""
        if not self._client:
            raise SessionExpired("No active session")

        params = kwargs.get("params", {}) or {}
        if "sh" not in params:
            params["sh"] = self.secure_hash
        params["a"] = str(int(time.time() * 1000))
        kwargs["params"] = params

        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError:
            logger.exception("HTTP error on %s %s", method, path)
            raise

        self._last_request_at = time.time()

        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if "needLogin" in location or "submod=login" in location:
                logger.warning("Session expired: redirected to %s (from %s %s)", location, method, path)
                return None
            logger.info("Redirected to %s (from %s %s), following", location, method, path)
            resp = await self._client.request("GET", location)
            html = resp.text
            if GameParser.is_session_expired(html):
                logger.warning("Session expired: login page detected after redirect from %s %s", method, path)
                return None
            new_sh = GameParser.parse_secure_hash(html)
            if new_sh and new_sh != self.secure_hash:
                logger.debug("Secure hash rotated: %s → %s", self.secure_hash[:8], new_sh[:8])
                self.secure_hash = new_sh
            return html

        if resp.status_code >= 400:
            logger.error("HTTP %d on %s %s", resp.status_code, method, path)
            return None

        html = resp.text

        if GameParser.is_session_expired(html):
            logger.warning("Session expired: login page detected in response to %s %s", method, path)
            return None

        new_sh = GameParser.parse_secure_hash(html)
        if new_sh and new_sh != self.secure_hash:
            logger.debug("Secure hash rotated: %s → %s", self.secure_hash[:8], new_sh[:8])
            self.secure_hash = new_sh

        return html

    async def _request(self, method: str, path: str, **kwargs) -> str:
        if not self._client:
            raise SessionExpired("No active session")

        async with self._semaphore:
            await self._enforce_delay()

            html = await self._request_raw(method, path, **kwargs)

            if html is None:
                self._connected = False
                for cb in self._on_session_expired:
                    await cb()
                raise SessionExpired("Session expired — redirected away from game")

            return html

    async def _enforce_delay(self) -> None:
        if self._last_request_at:
            elapsed = time.time() - self._last_request_at
            delay = random.uniform(self.settings.min_delay, self.settings.max_delay)
            remaining = delay - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)

    def on_session_expired(self, callback) -> None:
        self._on_session_expired.append(callback)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
