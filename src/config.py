import os
import platform
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings


def _default_data_dir() -> str:
    system = platform.system()
    if system == "Darwin":
        return str(Path.home() / "Library" / "Application Support" / "Gladbot")
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return str(appdata / "Gladbot")
    return str(Path.home() / ".gladbot")


class ModuleConfig(BaseModel):
    enabled: bool = False
    settings: dict = {}


class TrainingWeights(BaseModel):
    strength: int = 0
    dexterity: int = 2
    agility: int = 2
    constitution: int = 0
    charisma: int = 1
    intelligence: int = 1


class EquipmentConfig(BaseModel):
    sell_below_quality: int = 2
    compare_to_equipped: bool = True
    auto_equip: bool = True


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    data_dir: str = _default_data_dir()

    min_delay: float = 1.0
    max_delay: float = 5.0
    jitter_pct: float = 0.10

    heal_threshold: float = 0.5
    gold_reserve: int = 1000

    training_weights: TrainingWeights = TrainingWeights()
    equipment: EquipmentConfig = EquipmentConfig()


QUALITY_NAMES = {0: "white", 1: "green", 2: "blue", 3: "purple", 4: "orange", 5: "red"}
QUALITY_FROM_NAME = {v: k for k, v in QUALITY_NAMES.items()}

STAT_NAMES = ["strength", "dexterity", "agility", "constitution", "charisma", "intelligence"]

EQUIPMENT_SLOTS = {
    1: "helmet", 2: "armor", 3: "shield", 4: "gloves",
    5: "shoes", 6: "ring_left", 7: "ring_right", 8: "food",
    9: "amulet", 10: "weapon", 11: "mount",
}

INVENTORY_BAG_ID = 512
SMELTERY_BAG_ID = 514

DUNGEON_LOCATIONS = {0: "loc_0", 1: "loc_1", 2: "loc_2", 3: "loc_3", 4: "loc_4", 5: "loc_5"}

ARENA_TYPES = {1: "arena", 2: "provinciarum", 3: "circus"}
