from __future__ import annotations

import logging

from src.bot.base import BaseModule
from src.config import INVENTORY_BAG_ID
from src.session.manager import SessionManager
from src.session.parser import GameParser

logger = logging.getLogger(__name__)


class PackagesModule(BaseModule):
    name = "packages"
    min_level = 1

    def __init__(self, session: SessionManager) -> None:
        super().__init__(session)
        self.config: dict = {}

    async def tick(self) -> float:
        html = await self.session.get(
            "index.php",
            params={"mod": "packages", "f": "0", "fq": "-1", "qry": "", "page": "1"},
        )
        packages = GameParser.parse_package_items(html)

        if not packages:
            self._last_result = "No packages"
            return 120

        inv_html = await self.session.get(
            "ajax.php",
            params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)},
        )

        moved = 0
        for pkg in packages:
            free_slot = GameParser.parse_inventory_free_slot(inv_html, bag_id=INVENTORY_BAG_ID)
            if not free_slot:
                self._last_result = f"Inventory full, moved {moved}/{len(packages)}"
                logger.warning("Inventory full after moving %d items", moved)
                return 120
            x, y = free_slot
            await self.session.post(
                "ajax.php",
                params={
                    "mod": "inventory",
                    "submod": "move",
                    "from": f"-{pkg.package_id}",
                    "fromX": "1",
                    "fromY": "1",
                    "to": str(INVENTORY_BAG_ID),
                    "toX": str(x),
                    "toY": str(y),
                    "amount": "1",
                },
            )
            moved += 1
            logger.info("Moved package %s to inventory (%d,%d)", pkg.package_id, x, y)

            inv_html = await self.session.get(
                "ajax.php",
                params={"mod": "inventory", "submod": "loadBag", "bag": str(INVENTORY_BAG_ID)},
            )

        self._last_result = f"Collected {moved} packages"
        return 120
