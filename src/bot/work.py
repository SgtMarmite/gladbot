from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)

DEFAULT_WORK_DURATION_SEC = 8 * 3600


class WorkModule(BaseModule):
    name = "work"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {"job_type": 4, "work_duration": 1}

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "work"})

        status = GameParser.parse_work_status(html)
        if status["working"]:
            cooldown = status["cooldown"]
            if cooldown > 0:
                self._last_result = f"Working, {cooldown}s remaining"
                logger.info("Already working, cooldown %ds", cooldown)
                return cooldown + 10
            self._last_result = "Work finished, collecting"
            return 5

        job_type = self.config.get("job_type", 4)
        duration = self.config.get("work_duration", 1)

        result_html = await self.session.post(
            "index.php",
            params={"mod": "work", "submod": "start"},
            data={"dollForJob7": "1", "timeToWork": str(duration), "jobType": str(job_type)},
        )

        cooldown = GameParser.parse_work_cooldown(result_html)
        if cooldown > 0:
            self._last_result = f"Started work (type={job_type}, dur={duration}h), wait {cooldown}s"
            logger.info("Started work job_type=%d duration=%dh, cooldown=%ds", job_type, duration, cooldown)
            return cooldown + 10

        work_status = GameParser.parse_work_status(result_html)
        if work_status["working"]:
            cd = work_status["cooldown"] or DEFAULT_WORK_DURATION_SEC
            self._last_result = f"Work started, cooldown {cd}s"
            return cd + 10

        self._last_result = "Work started"
        return DEFAULT_WORK_DURATION_SEC
