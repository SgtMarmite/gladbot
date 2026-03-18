from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.api.websocket import ConnectionManager
from src.bot.engine import BotEngine
from src.session.manager import SessionExpired, SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)

router = APIRouter()

_session: SessionManager | None = None
_engine: BotEngine | None = None
_ws_manager: ConnectionManager | None = None
_stats_task: asyncio.Task | None = None


class SessionInjectRequest(BaseModel):
    url: str
    cookies: dict[str, str] | None = None
    cookie_header: str | None = None


class ModuleUpdateRequest(BaseModel):
    enabled: bool | None = None
    config: dict | None = None


def init_routes(session: SessionManager, engine: BotEngine, ws_manager: ConnectionManager) -> None:
    global _session, _engine, _ws_manager
    _session = session
    _engine = engine
    _ws_manager = ws_manager


@router.post("/api/session/inject")
async def session_inject(req: SessionInjectRequest):
    cookies = req.cookies or {}
    if req.cookie_header:
        for pair in req.cookie_header.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                cookies[k.strip()] = v.strip()
    logger.info("Inject request: url=%s, cookies=%s", req.url[:80], list(cookies.keys()))
    ok = await _session.inject_from_url(req.url, cookies if cookies else None)
    if ok:
        await _ws_manager.broadcast_session_status(True, _session.server_id)
        _start_stats_loop()
    else:
        await _ws_manager.broadcast_session_status(False)
    return {
        "ok": ok,
        "server": _session.server_id,
        "needs_cookies": not ok,
        "message": "Connected" if ok else "Session requires cookies. Use the bookmarklet on the game page.",
    }


@router.get("/api/session/status")
async def session_status():
    return {"connected": _session.connected, "server": _session.server_id}


@router.get("/api/stats")
async def get_stats():
    if not _session.connected:
        return {"error": "Not connected"}
    html = await _session.get("index.php", params={"mod": "overview"})
    stats = GameParser.parse_player_stats(html)
    return {
        "hp_current": stats.hp_current, "hp_max": stats.hp_max,
        "gold": stats.gold, "level": stats.level,
        "xp_current": stats.xp_current, "xp_max": stats.xp_max,
        "expedition_points": stats.expedition_points, "expedition_max": stats.expedition_max,
        "dungeon_points": stats.dungeon_points, "dungeon_max": stats.dungeon_max,
    }


@router.get("/api/modules")
async def list_modules():
    level = _engine._player_level
    return [
        mod.status(next_run_in=_engine.get_next_run_in(name), player_level=level).__dict__
        for name, mod in _engine.modules.items()
    ]


@router.put("/api/modules/{name}")
async def update_module(name: str, req: ModuleUpdateRequest):
    mod = _engine.modules.get(name)
    if not mod:
        return {"error": "Module not found"}
    if req.enabled is not None:
        mod.enabled = req.enabled
    if req.config is not None:
        mod.configure(req.config)
    await _ws_manager.broadcast_modules(await _get_modules_data())
    return {"ok": True, "module": mod.status(player_level=_engine._player_level).__dict__}


@router.post("/api/bot/start")
async def bot_start():
    if not _session.connected:
        return {"error": "Not connected"}
    _engine.start()
    return {"ok": True, "running": _engine.running}


@router.post("/api/bot/stop")
async def bot_stop():
    _engine.stop()
    return {"ok": True, "running": _engine.running}


@router.get("/api/bot/status")
async def bot_status():
    return {"running": _engine.running}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await _ws_manager.connect(ws, session_connected=_session.connected, server=_session.server_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_manager.disconnect(ws)


async def _get_modules_data() -> list[dict]:
    level = _engine._player_level
    return [
        mod.status(next_run_in=_engine.get_next_run_in(name), player_level=level).__dict__
        for name, mod in _engine.modules.items()
    ]


def _start_stats_loop() -> None:
    global _stats_task
    if _stats_task and not _stats_task.done():
        return
    _stats_task = asyncio.create_task(_stats_broadcast_loop())


async def _stats_broadcast_loop() -> None:
    while _session.connected:
        try:
            html = await _session.get("index.php", params={"mod": "overview"})
            stats = GameParser.parse_player_stats(html)
            _engine.update_player_level(stats.level)
            await _ws_manager.broadcast_session_status(_session.connected, _session.server_id)
            await _ws_manager.broadcast_stats({
                "hp_current": stats.hp_current, "hp_max": stats.hp_max,
                "gold": stats.gold, "level": stats.level,
                "xp_current": stats.xp_current, "xp_max": stats.xp_max,
            })
            await _ws_manager.broadcast_modules(await _get_modules_data())
        except SessionExpired:
            logger.warning("Stats loop: session expired, stopping")
            await _ws_manager.broadcast_session_status(False)
            break
        except Exception:
            logger.exception("Stats broadcast error")
        await asyncio.sleep(15)
