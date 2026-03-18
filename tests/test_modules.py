import pytest

from src.bot.arena import ArenaModule
from src.bot.base import BaseModule, ModuleStatus
from src.bot.dungeon import DungeonModule
from src.bot.engine import BotEngine
from src.bot.equipment import EquipmentModule
from src.bot.expedition import ExpeditionModule, best_location_for_level
from src.bot.inventory import InventoryModule
from src.bot.packages import PackagesModule
from src.bot.quests import QuestsModule
from src.bot.smelting import SmeltingModule
from src.bot.training import TrainingModule
from src.bot.work import WorkModule
from src.config import Settings
from src.session.manager import SessionManager


@pytest.fixture
def session():
    return SessionManager(Settings())


class TestBaseModule:
    def test_status(self, session):
        inv = InventoryModule(session)
        inv.enabled = True
        status = inv.status(next_run_in=30, player_level=5)
        assert status.name == "inventory"
        assert status.enabled is True
        assert status.next_run_in == 30
        assert status.locked is False

    def test_level_lock(self, session):
        dungeon = DungeonModule(session)
        status = dungeon.status(player_level=1)
        assert status.locked is True
        assert "level 3" in status.lock_reason.lower()

    def test_configure(self, session):
        exp = ExpeditionModule(session)
        exp.configure({"location": 2, "stage": 3})
        assert exp.config["location"] == 2
        assert exp.config["stage"] == 3


class TestEquipmentModule:
    def test_is_better(self):
        from src.session.parser import InventoryItem
        new = InventoryItem(stats={"strength": 10, "dexterity": 5})
        old = InventoryItem(stats={"strength": 5, "dexterity": 3})
        assert EquipmentModule._is_better(new, old) is True
        assert EquipmentModule._is_better(old, new) is False

    def test_is_worse(self):
        from src.session.parser import InventoryItem
        weak = InventoryItem(stats={"strength": 2})
        strong = InventoryItem(stats={"strength": 10, "armor": 5})
        assert EquipmentModule._is_worse(weak, strong) is True


class TestTrainingModule:
    def test_default_weights(self, session):
        mod = TrainingModule(session)
        weights = mod.config["priority_weights"]
        assert weights["dexterity"] == 2
        assert weights["agility"] == 2
        assert weights["strength"] == 0


class TestBotEngine:
    def test_register(self, session):
        engine = BotEngine(session)
        inv = InventoryModule(session)
        engine.register(inv)
        assert "inventory" in engine.modules

    def test_start_stop(self, session):
        engine = BotEngine(session)
        assert engine.running is False

    def test_level_update(self, session):
        engine = BotEngine(session)
        engine.update_player_level(15)
        assert engine._player_level == 15

    def test_next_run_in(self, session):
        engine = BotEngine(session)
        inv = InventoryModule(session)
        engine.register(inv)
        assert engine.get_next_run_in("inventory") == 0


class TestWorkModule:
    def test_defaults(self, session):
        mod = WorkModule(session)
        assert mod.name == "work"
        assert mod.min_level == 1
        assert mod.config["job_type"] == 4
        assert mod.config["work_duration"] == 1

    def test_configure(self, session):
        mod = WorkModule(session)
        mod.configure({"job_type": 2, "work_duration": 4})
        assert mod.config["job_type"] == 2
        assert mod.config["work_duration"] == 4


class TestPackagesModule:
    def test_defaults(self, session):
        mod = PackagesModule(session)
        assert mod.name == "packages"
        assert mod.min_level == 1


class TestSmeltingModule:
    def test_defaults(self, session):
        mod = SmeltingModule(session)
        assert mod.name == "smelting"
        assert mod.min_level == 10
        assert mod.config["max_quality"] == 1

    def test_level_lock(self, session):
        mod = SmeltingModule(session)
        status = mod.status(player_level=5)
        assert status.locked is True
        assert "level 10" in status.lock_reason.lower()


class TestExpeditionAutoLocation:
    def test_level_1(self):
        loc, stage = best_location_for_level(1)
        assert loc == 4
        assert stage == 4

    def test_level_20(self):
        loc, stage = best_location_for_level(20)
        assert loc == 8
        assert stage == 4

    def test_level_40(self):
        loc, stage = best_location_for_level(40)
        assert loc == 12
        assert stage == 4

    def test_level_15(self):
        loc, stage = best_location_for_level(15)
        assert loc == 4
        assert stage == 4


class TestExpeditionConfig:
    def test_speed_factor(self, session):
        mod = ExpeditionModule(session)
        assert mod.config["speed_factor"] == 1
        assert mod.config["auto_location"] is True


class TestDungeonConfig:
    def test_speed_factor(self, session):
        mod = DungeonModule(session)
        assert mod.config["speed_factor"] == 1


class TestInventoryAutoFood:
    def test_default_auto_buy(self, session):
        mod = InventoryModule(session)
        assert mod.config.get("auto_buy_food", True) is True


class TestAllModulesRegister:
    def test_all_modules(self, session):
        engine = BotEngine(session)
        modules = [
            InventoryModule(session),
            EquipmentModule(session),
            TrainingModule(session),
            ExpeditionModule(session),
            DungeonModule(session),
            ArenaModule(session),
            QuestsModule(session),
            WorkModule(session),
            PackagesModule(session),
            SmeltingModule(session),
        ]
        for mod in modules:
            engine.register(mod)
        assert len(engine.modules) == 10
        names = set(engine.modules.keys())
        assert names == {
            "inventory", "equipment", "training", "expedition",
            "dungeon", "arena", "quests", "work", "packages", "smelting",
        }
