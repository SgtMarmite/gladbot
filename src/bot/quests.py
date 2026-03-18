from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class QuestsModule(BaseModule):
    name = "quests"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {"auto_cycle": True}

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "quests"})
        slots = GameParser.parse_quest_slots(html)

        finished = [q for q in slots if q.status == "finished"]
        for q in finished:
            await self.session.get(
                "index.php",
                params={"mod": "quests", "submod": "finishQuest", "questPos": str(q.position)},
            )
            logger.info("Finished quest pos=%d", q.position)

        restartable = [q for q in slots if q.status == "restartable"]
        for q in restartable:
            await self.session.get(
                "index.php",
                params={"mod": "quests", "submod": "restartQuest", "questPos": str(q.position)},
            )
            logger.info("Restarted quest pos=%d", q.position)

        html = await self.session.get("index.php", params={"mod": "quests"})
        slots = GameParser.parse_quest_slots(html)

        available = [q for q in slots if q.status == "available"]
        for q in available:
            await self.session.get(
                "index.php",
                params={"mod": "quests", "submod": "startQuest", "questPos": str(q.position)},
            )
            logger.info("Started quest pos=%d", q.position)

        active = [q for q in slots if q.status == "active"]
        if not active and not available and self.config.get("auto_cycle", True):
            await self.session.get("index.php", params={"mod": "quests", "submod": "resetQuests"})
            logger.info("Reset quest cycle")

        total_actions = len(finished) + len(restartable) + len(available)
        self._last_result = f"Actions: {total_actions} (fin={len(finished)}, rst={len(restartable)}, new={len(available)})"
        return 120
