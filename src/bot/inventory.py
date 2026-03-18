from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.config import INVENTORY_BAG_ID
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class InventoryModule(BaseModule):
    name = "inventory"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config = {"heal_threshold": 0.5}

    async def tick(self) -> float:
        html = await self.session.get("index.php", params={"mod": "overview"})
        hp_cur, hp_max = GameParser.parse_hp(html)

        if hp_max == 0:
            self._last_result = "Could not parse HP"
            return 30

        ratio = hp_cur / hp_max
        threshold = self.config.get("heal_threshold", 0.5)

        if ratio < threshold:
            healed = await self._eat_food()
            if healed:
                self._last_result = f"Healed (HP was {ratio:.0%})"
            else:
                self._last_result = f"No food available (HP {ratio:.0%})"
        else:
            self._last_result = f"HP OK ({ratio:.0%})"

        return 30

    async def _eat_food(self) -> bool:
        html = await self.session.get(
            "ajax.php",
            params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)},
        )
        food_items = GameParser.parse_food_items(html, bag_id=INVENTORY_BAG_ID)

        if not food_items:
            bought = await self._buy_food_from_npc()
            if not bought:
                return False
            html = await self.session.get(
                "ajax.php",
                params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)},
            )
            food_items = GameParser.parse_food_items(html, bag_id=INVENTORY_BAG_ID)
            if not food_items:
                return False

        food = food_items[0]
        await self.session.post(
            "ajax.php",
            params={
                "mod": "inventory",
                "submod": "move",
                "from": str(INVENTORY_BAG_ID),
                "fromX": str(food.x),
                "fromY": str(food.y),
                "to": "8",
                "toX": "1",
                "toY": "1",
                "amount": "1",
                "doll": "1",
            },
        )
        logger.info("Ate food at (%d,%d)", food.x, food.y)
        return True

    async def _buy_food_from_npc(self) -> bool:
        if not self.config.get("auto_buy_food", True):
            return False

        shop_html = await self.session.get("index.php", params={"mod": "inventory", "sub": "4"})
        food_items = GameParser.parse_npc_shop_food(shop_html)

        if not food_items:
            logger.debug("No food found in NPC shop")
            return False

        food = food_items[0]
        await self.session.get(
            "index.php",
            params={"mod": "inventory", "sub": "4", "submod": "buyItem", "buyItemId": food.item_id},
        )
        logger.info("Bought food %s from NPC shop", food.item_id)
        return True

    async def check_and_heal(self, html: str | None = None) -> bool:
        if html is None:
            html = await self.session.get("index.php", params={"mod": "overview"})
        hp_cur, hp_max = GameParser.parse_hp(html)
        if hp_max == 0:
            return False
        ratio = hp_cur / hp_max
        threshold = self.config.get("heal_threshold", 0.5)
        if ratio < threshold:
            return await self._eat_food()
        return False
