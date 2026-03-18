from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)

DEFAULT_ARENA_COOLDOWN = 900


class ArenaModule(BaseModule):
    name = "arena"
    min_level = 2

    def __init__(self, session: SessionManager, inventory_module=None) -> None:
        super().__init__(session)
        self.inventory = inventory_module
        self.config = {"arena_type": 1, "max_level_diff": 5}

    async def tick(self) -> float:
        arena_type = self.config.get("arena_type", 1)

        if arena_type == 1:
            return await self._arena_local()
        else:
            return await self._arena_server(arena_type)

    async def _arena_local(self) -> float:
        html = await self.session.get("index.php", params={"mod": "arena"})

        cooldown = GameParser.parse_arena_cooldown(html)
        if cooldown > 0:
            self._last_result = f"Arena on cooldown ({cooldown}s)"
            return cooldown

        opponents = GameParser.parse_arena_opponents(html)
        player_level = GameParser.parse_level(html)

        if not opponents:
            self._last_result = "No opponents available"
            return DEFAULT_ARENA_COOLDOWN

        max_diff = self.config.get("max_level_diff", 5)
        targets = [o for o in opponents if abs(o.level - player_level) <= max_diff]

        if not targets:
            self._last_result = "No suitable opponents"
            return DEFAULT_ARENA_COOLDOWN

        target = min(targets, key=lambda o: o.level)

        if self.inventory:
            await self.inventory.check_and_heal()

        result_html = await self.session.get(
            "ajax.php",
            params={"mod": "arena", "submod": "doCombat", "aType": "1", "opponentId": target.player_id},
        )
        logger.info("Arena fight vs %s (level %d)", target.name, target.level)

        cooldown = GameParser.parse_arena_cooldown(result_html)
        if cooldown <= 0:
            cooldown = DEFAULT_ARENA_COOLDOWN

        self._last_result = f"Fought {target.name} (lvl {target.level}), cd {cooldown}s"
        return cooldown

    async def _arena_server(self, arena_type: int) -> float:
        html = await self.session.get(
            "index.php", params={"mod": "arena", "submod": "serverArena", "aType": str(arena_type)}
        )

        cooldown = GameParser.parse_arena_cooldown(html)
        if cooldown > 0:
            self._last_result = f"Server arena on cooldown ({cooldown}s)"
            return cooldown

        opponents = GameParser.parse_arena_opponents(html)
        player_level = GameParser.parse_level(html)

        if not opponents:
            await self.session.post(
                "index.php",
                params={"mod": "arena", "submod": "getNewOpponents", "aType": str(arena_type)},
                data={"actionButton": "Search"},
            )
            self._last_result = "Refreshed opponents"
            return 60

        max_diff = self.config.get("max_level_diff", 5)
        targets = [o for o in opponents if abs(o.level - player_level) <= max_diff]

        if not targets:
            self._last_result = "No suitable opponents"
            return DEFAULT_ARENA_COOLDOWN

        target = min(targets, key=lambda o: o.level)

        if self.inventory:
            await self.inventory.check_and_heal()

        params = {
            "mod": "arena", "submod": "doCombat", "aType": str(arena_type),
            "opponentId": target.player_id,
        }
        if target.server_id:
            params["serverId"] = target.server_id
            params["country"] = target.server_id.split("-")[0] if "-" in target.server_id else ""

        result_html = await self.session.get("ajax.php", params=params)
        logger.info("Server arena (type %d) fight vs %s", arena_type, target.name)

        cooldown = GameParser.parse_arena_cooldown(result_html)
        if cooldown <= 0:
            cooldown = DEFAULT_ARENA_COOLDOWN

        self._last_result = f"Fought {target.name} (lvl {target.level}), cd {cooldown}s"
        return cooldown
