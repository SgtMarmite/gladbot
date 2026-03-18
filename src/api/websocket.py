from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._log_buffer: list[dict] = []
        self._max_buffer = 200

    async def connect(self, ws: WebSocket, session_connected: bool = False, server: str = "") -> None:
        await ws.accept()
        self._connections.append(ws)
        await ws.send_json({"type": "session", "connected": session_connected, "server": server})
        if self._log_buffer:
            await ws.send_json({"type": "log_history", "entries": self._log_buffer[-50:]})

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, data: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_log(self, entry: dict) -> None:
        self._log_buffer.append(entry)
        if len(self._log_buffer) > self._max_buffer:
            self._log_buffer = self._log_buffer[-self._max_buffer:]
        await self.broadcast({"type": "log", "entry": entry})

    async def broadcast_stats(self, stats: dict) -> None:
        await self.broadcast({"type": "stats", "data": stats})

    async def broadcast_modules(self, modules: list[dict]) -> None:
        await self.broadcast({"type": "modules", "data": modules})

    async def broadcast_session_status(self, connected: bool, server: str = "") -> None:
        await self.broadcast({"type": "session", "connected": connected, "server": server})
