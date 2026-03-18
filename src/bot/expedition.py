from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)

POINT_REGEN_BASE_SECONDS = 5400

LEVEL_LOCATIONS = [
    (1, [(1, 1), (1, 2), (1, 3), (1, 4), (2, 1), (2, 2), (2, 3), (2, 4),
         (3, 1), (3, 2), (3, 3), (3, 4), (4, 1), (4, 2), (4, 3), (4, 4)]),
    (20, [(5, 1), (5, 2), (5, 3), (5, 4), (6, 1), (6, 2), (6, 3), (6, 4),
          (7, 1), (7, 2), (7, 3), (7, 4), (8, 1), (8, 2), (8, 3), (8, 4)]),
    (40, [(9, 1), (9, 2), (9, 3), (9, 4), (10, 1), (10, 2), (10, 3), (10, 4),
          (11, 1), (11, 2), (11, 3), (11, 4), (12, 1), (12, 2), (12, 3), (12, 4)]),
]


def best_location_for_level(level: int) -> tuple[int, int]:
    best_loc, best_stage = 4, 4
    for min_level, locations in LEVEL_LOCATIONS:
        if level >= min_level:
            best_loc, best_stage = locations[-1]
    return best_loc, best_stage


class ExpeditionModule(BaseModule):
    name = "expedition"
    min_level = 1

    def __init__(self, session: SessionManager, inventory_module=None) -> None:
        super().__init__(session)
        self.inventory = inventory_module
        self.config = {"location": 4, "stage": 4, "auto_location": True, "speed_factor": 1}

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "location", "loc": "0"})
        exp_cur, exp_max = GameParser.parse_expedition_points(html)
        player_level = GameParser.parse_level(html)

        if exp_cur <= 0:
            speed = self.config.get("speed_factor", 1)
            regen_time = POINT_REGEN_BASE_SECONDS / speed
            self._last_result = f"No points, regen in {int(regen_time)}s"
            logger.info("No expedition points, waiting %ds for regen", int(regen_time))
            return regen_time

        if self.inventory:
            await self.inventory.check_and_heal(html)

        if self.config.get("auto_location", True) and player_level > 0:
            location, stage = best_location_for_level(player_level)
        else:
            location = self.config.get("location", 4)
            stage = self.config.get("stage", 4)

        result_html = await self.session.get(
            "ajax.php",
            params={
                "mod": "location",
                "submod": "attack",
                "location": str(location),
                "stage": str(stage),
                "premium": "0",
            },
        )

        cooldown = GameParser.parse_cooldown(result_html)
        if cooldown > 0:
            self._last_result = f"Attack loc={location} stage={stage}, cd {cooldown}s ({exp_cur - 1}/{exp_max} pts)"
            logger.info("Expedition loc=%d stage=%d, cooldown %ds", location, stage, cooldown)
            return cooldown

        self._last_result = f"Attack sent loc={location} stage={stage}"
        return 60
