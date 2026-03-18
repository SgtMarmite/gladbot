from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)

DUNGEON_POINT_REGEN_BASE_SECONDS = 5400


class DungeonModule(BaseModule):
    name = "dungeon"
    min_level = 3

    def __init__(self, session: SessionManager, inventory_module=None) -> None:
        super().__init__(session)
        self.inventory = inventory_module
        self.config = {"location": 0, "difficulty": "Normal", "speed_factor": 1}

    async def tick(self) -> float:
        location = self.config.get("location", 0)
        difficulty = self.config.get("difficulty", "Normal")

        html = await self.session.get("index.php", params={"mod": "dungeon", "loc": str(location)})

        dng_cur, dng_max = GameParser.parse_dungeon_points(html)
        if dng_cur <= 0 and dng_max > 0:
            speed = self.config.get("speed_factor", 1)
            regen_time = DUNGEON_POINT_REGEN_BASE_SECONDS / speed
            self._last_result = f"No dungeon points, regen in {int(regen_time)}s"
            logger.info("No dungeon points, waiting %ds for regen", int(regen_time))
            return regen_time

        dungeon_id = GameParser.parse_dungeon_id(html)
        enemies = GameParser.parse_dungeon_enemies(html)

        if not dungeon_id or not enemies:
            diff_key = "dif1" if difficulty == "Normal" else "dif2"
            await self.session.post(
                "index.php",
                params={"mod": "dungeon", "loc": str(location)},
                data={diff_key: difficulty},
            )
            html = await self.session.get("index.php", params={"mod": "dungeon", "loc": str(location)})
            dungeon_id = GameParser.parse_dungeon_id(html)
            enemies = GameParser.parse_dungeon_enemies(html)

        if not dungeon_id:
            self._last_result = "Could not start dungeon"
            return 300

        fights = 0
        for enemy in enemies:
            if enemy.get("defeated"):
                continue

            if self.inventory:
                await self.inventory.check_and_heal()

            await self.session.get(
                "ajax.php",
                params={
                    "mod": "dungeon",
                    "submod": "doDungeonFight",
                    "did": dungeon_id,
                    "posi": str(enemy["position"]),
                },
            )
            fights += 1
            logger.info("Dungeon fight did=%s pos=%d", dungeon_id, enemy["position"])

        self._last_result = f"Dungeon done, {fights} fights"
        return 600
