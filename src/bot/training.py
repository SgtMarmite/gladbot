from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.config import STAT_NAMES
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class TrainingModule(BaseModule):
    name = "training"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {
            "priority_weights": {
                "strength": 0, "dexterity": 2, "agility": 2,
                "constitution": 0, "charisma": 1, "intelligence": 1,
            },
            "gold_reserve": 1000,
        }

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "training"})
        gold = GameParser.parse_gold(html)
        costs = GameParser.parse_training_costs(html)
        level = GameParser.parse_level(html)
        reserve = self.config.get("gold_reserve", 1000)
        weights = self.config.get("priority_weights", {})

        stat_cap = level * 5

        trainable = []
        for stat in STAT_NAMES:
            w = weights.get(stat, 0)
            if w <= 0:
                continue
            cost = costs.get(stat)
            if cost is None:
                continue
            if gold - cost < reserve:
                continue
            trainable.append((stat, cost, w))

        if not trainable:
            self._last_result = f"Nothing to train (gold={gold}, reserve={reserve})"
            return 120

        trainable.sort(key=lambda x: (-x[2], x[1]))
        stat, cost, _ = trainable[0]

        await self.session.post(
            "ajax.php",
            params={"mod": "training", "submod": "doTraining", "stat": stat},
        )
        logger.info("Trained %s for %d gold", stat, cost)
        self._last_result = f"Trained {stat} (cost {cost}g)"
        return 60

    async def get_training_status(self) -> dict:
        html = await self.session.get("index.php", params={"mod": "training"})
        return {
            "costs": GameParser.parse_training_costs(html),
            "gold": GameParser.parse_gold(html),
        }
