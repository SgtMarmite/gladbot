from __future__ import annotations

import asyncio
import logging
import random
import time

from src.bot.base import BaseModule
from src.session.manager import SessionExpired, SessionManager

logger = logging.getLogger(__name__)

MAX_BACKOFF = 300
BASE_BACKOFF = 10


class BotEngine:
    def __init__(self, session: SessionManager) -> None:
        self.session = session
        self.modules: dict[str, BaseModule] = {}
        self._next_run: dict[str, float] = {}
        self._fail_count: dict[str, int] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._log_callbacks: list = []
        self._player_level: int = 0

    def register(self, module: BaseModule) -> None:
        self.modules[module.name] = module
        self._next_run[module.name] = 0
        self._fail_count[module.name] = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Bot engine started")

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Bot engine stopped")

    @property
    def running(self) -> bool:
        return self._running

    def on_log(self, callback) -> None:
        self._log_callbacks.append(callback)

    async def _emit_log(self, module: str, message: str, status: str = "OK") -> None:
        entry = {"time": time.time(), "module": module, "message": message, "status": status}
        for cb in self._log_callbacks:
            try:
                await cb(entry)
            except Exception:
                pass

    async def _loop(self) -> None:
        while self._running:
            now = time.time()
            ready = [
                (name, mod)
                for name, mod in self.modules.items()
                if mod.enabled
                and not mod.status(player_level=self._player_level).locked
                and self._next_run.get(name, 0) <= now
            ]

            if not ready:
                await asyncio.sleep(1)
                continue

            ready.sort(key=lambda x: self._next_run.get(x[0], 0))
            name, module = ready[0]

            try:
                module._running = True
                wait_seconds = await module.tick()
                module._running = False
                self._fail_count[name] = 0

                jitter = wait_seconds * random.uniform(0, self.session.settings.jitter_pct)
                self._next_run[name] = time.time() + wait_seconds + jitter
                result_msg = module._last_result or "OK"
                await self._emit_log(name, result_msg)

            except SessionExpired:
                module._running = False
                self._running = False
                module._last_result = "Session expired"
                await self._emit_log(name, "Session expired — bot paused", "ERROR")
                logger.warning("Session expired, pausing all modules")
                break

            except Exception as e:
                module._running = False
                self._fail_count[name] = self._fail_count.get(name, 0) + 1
                backoff = min(BASE_BACKOFF * (2 ** self._fail_count[name]), MAX_BACKOFF)
                self._next_run[name] = time.time() + backoff
                module._last_result = f"Error: {e}"
                await self._emit_log(name, f"Error: {e}, retry in {backoff:.0f}s", "ERROR")
                logger.exception("Module %s failed (attempt %d)", name, self._fail_count[name])

    def get_next_run_in(self, name: str) -> float:
        remaining = self._next_run.get(name, 0) - time.time()
        return max(0, remaining)

    def update_player_level(self, level: int) -> None:
        self._player_level = level
