from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.config import INVENTORY_BAG_ID, QUALITY_NAMES
from src.session.manager import SessionManager
from src.session.parser import GameParser, InventoryItem

logger = logging.getLogger(__name__)


class EquipmentModule(BaseModule):
    name = "equipment"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {
            "sell_below_quality": 2,
            "compare_to_equipped": True,
            "auto_equip": True,
        }

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "overview"})
        equipped = GameParser.parse_equipment_slots(html)

        bag_html = await self.session.get(
            "ajax.php", params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)}
        )
        bag_items = GameParser.parse_inventory_items(bag_html, bag_id=INVENTORY_BAG_ID)

        sold = 0
        equipped_count = 0

        for item in bag_items:
            if item.is_food:
                continue

            should_sell = False
            if item.quality < self.config.get("sell_below_quality", 2):
                should_sell = True

            if self.config.get("compare_to_equipped", True) and not should_sell:
                current = equipped.get(item.slot_type)
                if current and self._is_worse(item, current):
                    should_sell = True

            if self.config.get("auto_equip", True) and not should_sell and item.slot_type:
                current = equipped.get(item.slot_type)
                if current is None or self._is_better(item, current):
                    await self._equip_item(item)
                    equipped[item.slot_type] = item
                    equipped_count += 1
                    continue

            if should_sell:
                await self._sell_item(item)
                sold += 1

        self._last_result = f"Sold {sold}, equipped {equipped_count}"
        return 120

    @staticmethod
    def _total_stats(item: InventoryItem) -> int:
        return sum(item.stats.values())

    @staticmethod
    def _is_better(new: InventoryItem, current: InventoryItem) -> bool:
        return EquipmentModule._total_stats(new) > EquipmentModule._total_stats(current)

    @staticmethod
    def _is_worse(new: InventoryItem, current: InventoryItem) -> bool:
        return EquipmentModule._total_stats(new) < EquipmentModule._total_stats(current)

    async def _equip_item(self, item: InventoryItem) -> None:
        await self.session.post(
            "ajax.php",
            params={
                "mod": "inventory",
                "submod": "move",
                "from": str(item.bag),
                "fromX": str(item.x),
                "fromY": str(item.y),
                "to": str(item.slot_type),
                "toX": "1",
                "toY": "1",
                "amount": "1",
                "doll": "1",
            },
        )
        logger.info("Equipped %s (quality %s)", item.name, QUALITY_NAMES.get(item.quality, "?"))

    async def _sell_item(self, item: InventoryItem) -> None:
        await self.session.post(
            "ajax.php",
            params={"mod": "inventory", "submod": "sellItem", "itemId": item.item_id},
        )
        logger.info("Sold %s (quality %s)", item.name, QUALITY_NAMES.get(item.quality, "?"))
