from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.session.manager import SessionManager


@dataclass
class ModuleStatus:
    name: str = ""
    enabled: bool = False
    running: bool = False
    next_run_in: float = 0
    last_result: str = ""
    config: dict = field(default_factory=dict)
    locked: bool = False
    lock_reason: str = ""


class BaseModule(ABC):
    name: str = ""
    min_level: int = 1

    def __init__(self, session: SessionManager) -> None:
        self.session = session
        self.enabled: bool = False
        self.config: dict = {}
        self._last_result: str = ""
        self._running: bool = False

    @abstractmethod
    async def tick(self) -> float:
        """Execute one cycle. Return seconds until next tick."""

    def status(self, next_run_in: float = 0, player_level: int = 0) -> ModuleStatus:
        locked = player_level < self.min_level if player_level else False
        return ModuleStatus(
            name=self.name,
            enabled=self.enabled,
            running=self._running,
            next_run_in=next_run_in,
            last_result=self._last_result,
            config=self.config,
            locked=locked,
            lock_reason=f"Requires level {self.min_level}" if locked else "",
        )

    def configure(self, settings: dict) -> None:
        self.config.update(settings)
