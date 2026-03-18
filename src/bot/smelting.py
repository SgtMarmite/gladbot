from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.config import INVENTORY_BAG_ID
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class SmeltingModule(BaseModule):
    name = "smelting"
    min_level = 10

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {"max_quality": 1, "slot": 1}

    async def tick(self) -> float:
        max_quality = self.config.get("max_quality", 1)
        slot = self.config.get("slot", 1)

        html = await self.session.get(
            "ajax.php",
            params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)},
        )
        items = GameParser.parse_inventory_items(html, bag_id=INVENTORY_BAG_ID)

        smeltable = [i for i in items if not i.is_food and i.quality <= max_quality and i.item_id]
        if not smeltable:
            self._last_result = "Nothing to smelt"
            return 300

        smelted = 0
        for item in smeltable:
            preview = await self.session.post(
                "ajax.php",
                data={
                    "mod": "forge",
                    "submod": "getSmeltingPreview",
                    "mode": "smelting",
                    "slot": str(slot),
                    "iid": item.item_id,
                },
            )
            if "error" in preview.lower():
                logger.debug("Cannot smelt item %s: %s", item.item_id, preview[:100])
                continue

            await self.session.post(
                "ajax.php",
                data={
                    "mod": "forge",
                    "submod": "rent",
                    "mode": "smelting",
                    "slot": str(slot),
                    "rent": "2",
                    "item": item.item_id,
                },
            )
            smelted += 1
            logger.info("Smelted item %s (%s, quality=%d)", item.item_id, item.name, item.quality)

        self._last_result = f"Smelted {smelted}/{len(smeltable)} items"
        return 300
