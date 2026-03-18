from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag


@dataclass
class PlayerStats:
    hp_current: int = 0
    hp_max: int = 0
    gold: int = 0
    level: int = 0
    xp_current: int = 0
    xp_max: int = 0
    expedition_points: int = 0
    expedition_max: int = 0
    dungeon_points: int = 0
    dungeon_max: int = 0


@dataclass
class PackageItem:
    package_id: str = ""
    name: str = ""
    quality: int = 0


@dataclass
class InventoryItem:
    item_id: str = ""
    name: str = ""
    quality: int = 0
    level: int = 0
    slot_type: int = 0
    bag: int = 0
    x: int = 0
    y: int = 0
    stats: dict = field(default_factory=dict)
    is_food: bool = False
    heal_amount: int = 0


@dataclass
class ArenaOpponent:
    player_id: str = ""
    name: str = ""
    level: int = 0
    server_id: str = ""


@dataclass
class QuestSlot:
    position: int = 0
    status: str = ""
    name: str = ""


class GameParser:

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def parse_secure_hash(html: str) -> str | None:
        m = re.search(r"var\s+secureHash\s*=\s*[\"']([a-f0-9]+)[\"']", html)
        if m:
            return m.group(1)
        m = re.search(r"sh=([a-f0-9]+)", html)
        return m.group(1) if m else None

    @staticmethod
    def parse_hp(html: str) -> tuple[int, int]:
        soup = GameParser._soup(html)
        hp_bar = soup.select_one("#header_values_hp_bar")
        if hp_bar:
            val = hp_bar.get("data-value")
            mx = hp_bar.get("data-max-value")
            if val and mx:
                return int(val), int(mx)
        hp_bar = soup.select_one("#header_trainer_bar .bar_text")
        if not hp_bar:
            hp_bar = soup.select_one("#header_trainer_bar span")
        if hp_bar:
            text = hp_bar.get_text(strip=True)
            m = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if m:
                return int(m.group(1)), int(m.group(2))
        m = re.search(r'globalData\.playerData\.hpActual\s*=\s*(\d+)', html)
        m2 = re.search(r'globalData\.playerData\.hpMax\s*=\s*(\d+)', html)
        if m and m2:
            return int(m.group(1)), int(m2.group(1))
        return 0, 0

    @staticmethod
    def parse_gold(html: str) -> int:
        soup = GameParser._soup(html)
        gold_el = soup.select_one("#sstat_gold_val")
        if gold_el:
            text = gold_el.get_text(strip=True).replace(".", "").replace(",", "")
            m = re.search(r"\d+", text)
            return int(m.group()) if m else 0
        m = re.search(r'globalData\.playerData\.gold\s*=\s*(\d+)', html)
        return int(m.group(1)) if m else 0

    @staticmethod
    def parse_level(html: str) -> int:
        soup = GameParser._soup(html)
        for selector in ("#header_values_level", "#char_level", "#header_trainer_level"):
            el = soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                m = re.search(r"\d+", text)
                if m:
                    return int(m.group())
        m = re.search(r'globalData\.playerData\.level\s*=\s*(\d+)', html)
        return int(m.group(1)) if m else 0

    @staticmethod
    def parse_xp(html: str) -> tuple[int, int]:
        soup = GameParser._soup(html)
        xp_bar = soup.select_one("#header_values_xp_bar")
        if xp_bar:
            tooltip = xp_bar.get("data-tooltip", "")
            m = re.search(r"(\d+)\s*/\s*(\d+)", tooltip.replace("\\", "").replace("&quot;", '"'))
            if m:
                return int(m.group(1)), int(m.group(2))
        xp_bar = soup.select_one("#header_trainer_xp .bar_text")
        if not xp_bar:
            xp_bar = soup.select_one("#header_trainer_xp span")
        if xp_bar:
            text = xp_bar.get_text(strip=True)
            m = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 0, 0

    @staticmethod
    def parse_expedition_points(html: str) -> tuple[int, int]:
        soup = GameParser._soup(html)
        cur_el = soup.select_one("#expeditionpoints_value_point")
        max_el = soup.select_one("#expeditionpoints_value_pointmax")
        if cur_el and max_el:
            cur = re.search(r"\d+", cur_el.get_text(strip=True))
            mx = re.search(r"\d+", max_el.get_text(strip=True))
            if cur and mx:
                return int(cur.group()), int(mx.group())
        exp_val = soup.select_one("#expeditionpoints_value")
        if exp_val:
            text = exp_val.get_text(strip=True)
            m = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 0, 0

    @staticmethod
    def parse_cooldown(html: str) -> int:
        m = re.search(r"var\s+cooldownTimer\s*=\s*(\d+)", html)
        if m:
            return int(m.group(1))
        m = re.search(r"cooldown[\"']?\s*:\s*(\d+)", html)
        return int(m.group(1)) if m else 0

    @staticmethod
    def parse_dungeon_enemies(html: str) -> list[dict]:
        soup = GameParser._soup(html)
        enemies = []
        for npc in soup.select(".dungeon_npc"):
            pos_attr = npc.get("data-posi", npc.get("id", ""))
            m = re.search(r"\d+", str(pos_attr))
            pos = int(m.group()) if m else 0
            defeated = "defeated" in npc.get("class", []) if isinstance(npc.get("class"), list) else False
            enemies.append({"position": pos, "defeated": defeated})
        return enemies

    @staticmethod
    def parse_dungeon_id(html: str) -> str | None:
        m = re.search(r"dungeonId\s*=\s*[\"']?(\d+)", html)
        if m:
            return m.group(1)
        m = re.search(r"did=(\d+)", html)
        return m.group(1) if m else None

    @staticmethod
    def parse_food_items(html: str, bag_id: int = 512) -> list[InventoryItem]:
        soup = GameParser._soup(html)
        items = []
        for item_el in soup.select(f'[data-bag="{bag_id}"] .ui-draggable, .inventory_item'):
            item = GameParser._parse_item_element(item_el)
            if item and item.is_food:
                items.append(item)
        return items

    @staticmethod
    def parse_inventory_items(html: str, bag_id: int | None = None) -> list[InventoryItem]:
        soup = GameParser._soup(html)
        items = []
        selector = ".ui-draggable, .inventory_item"
        for item_el in soup.select(selector):
            item = GameParser._parse_item_element(item_el)
            if item:
                if bag_id is None or item.bag == bag_id:
                    items.append(item)
        return items

    @staticmethod
    def _parse_item_element(el: Tag) -> InventoryItem | None:
        item_id = el.get("data-item-id", el.get("id", ""))
        if not item_id:
            return None

        tooltip = el.get("data-tooltip", el.get("title", ""))
        name = ""
        quality = 0
        level = 0
        is_food = False
        heal_amount = 0
        stats: dict = {}
        slot_type = 0

        if tooltip:
            name_m = re.search(r'class="item_name[^"]*"[^>]*>([^<]+)', tooltip)
            if name_m:
                name = name_m.group(1).strip()

            qual_m = re.search(r'quality[_-]?(\d+)', tooltip)
            if qual_m:
                quality = int(qual_m.group(1))

            level_m = re.search(r'(?:Level|Lvl|Stufe)\s*:?\s*(\d+)', tooltip, re.IGNORECASE)
            if level_m:
                level = int(level_m.group(1))

            if re.search(r'(?:heal|food|hp\s*\+)', tooltip, re.IGNORECASE):
                is_food = True
                heal_m = re.search(r'(?:hp\s*\+\s*(\d+)|(\d+)\s*(?:HP|health|heal))', tooltip, re.IGNORECASE)
                if heal_m:
                    heal_amount = int(heal_m.group(1) or heal_m.group(2))

            for stat_name in ["strength", "dexterity", "agility", "constitution", "charisma", "intelligence",
                              "armor", "damage", "block", "critical"]:
                stat_m = re.search(rf'{stat_name}\s*:?\s*\+?\s*(\d+)', tooltip, re.IGNORECASE)
                if stat_m:
                    stats[stat_name] = int(stat_m.group(1))

        bag = int(el.get("data-bag", 0))
        x = int(el.get("data-x", el.get("data-fromx", 0)))
        y = int(el.get("data-y", el.get("data-fromy", 0)))

        return InventoryItem(
            item_id=str(item_id), name=name, quality=quality, level=level,
            slot_type=slot_type, bag=bag, x=x, y=y, stats=stats,
            is_food=is_food, heal_amount=heal_amount,
        )

    @staticmethod
    def parse_arena_opponents(html: str) -> list[ArenaOpponent]:
        soup = GameParser._soup(html)
        opponents = []
        for row in soup.select(".arena_trainer_row, .arena_opponent"):
            name_el = row.select_one(".arena_trainer_name, .name")
            level_el = row.select_one(".arena_trainer_level, .level")
            fight_link = row.select_one("a[href*='opponentId'], a[href*='did=']")

            name = name_el.get_text(strip=True) if name_el else ""
            level = 0
            if level_el:
                m = re.search(r"\d+", level_el.get_text())
                level = int(m.group()) if m else 0

            player_id = ""
            server_id = ""
            if fight_link:
                href = fight_link.get("href", "")
                pid_m = re.search(r"opponentId=(\d+)", href)
                sid_m = re.search(r"serverId=([^&]+)", href)
                if pid_m:
                    player_id = pid_m.group(1)
                if sid_m:
                    server_id = sid_m.group(1)

            if player_id:
                opponents.append(ArenaOpponent(
                    player_id=player_id, name=name, level=level, server_id=server_id
                ))
        return opponents

    @staticmethod
    def parse_quest_slots(html: str) -> list[QuestSlot]:
        soup = GameParser._soup(html)
        quests = []
        for slot in soup.select(".quest_slot, .quest_container"):
            pos_attr = slot.get("data-questpos", slot.get("id", ""))
            m = re.search(r"\d+", str(pos_attr))
            pos = int(m.group()) if m else 0

            status = "empty"
            if slot.select_one(".quest_finish, [submod='finishQuest']"):
                status = "finished"
            elif slot.select_one(".quest_restart, [submod='restartQuest']"):
                status = "restartable"
            elif slot.select_one(".quest_start, [submod='startQuest']"):
                status = "available"
            elif slot.select_one(".quest_active, .quest_running"):
                status = "active"

            name_el = slot.select_one(".quest_name, .quest_title")
            name = name_el.get_text(strip=True) if name_el else ""

            quests.append(QuestSlot(position=pos, status=status, name=name))
        return quests

    @staticmethod
    def parse_training_costs(html: str) -> dict[str, int]:
        soup = GameParser._soup(html)
        costs: dict[str, int] = {}
        for row in soup.select(".training_row, .train_stat"):
            label = row.select_one(".training_name, .stat_name")
            cost_el = row.select_one(".training_cost, .cost")
            if label and cost_el:
                stat_name = label.get_text(strip=True).lower()
                cost_text = cost_el.get_text(strip=True).replace(".", "").replace(",", "")
                m = re.search(r"\d+", cost_text)
                if m:
                    costs[stat_name] = int(m.group())
        return costs

    @staticmethod
    def parse_player_stats(html: str) -> PlayerStats:
        hp_cur, hp_max = GameParser.parse_hp(html)
        xp_cur, xp_max = GameParser.parse_xp(html)
        exp_cur, exp_max = GameParser.parse_expedition_points(html)
        dng_cur, dng_max = GameParser.parse_dungeon_points(html)
        return PlayerStats(
            hp_current=hp_cur, hp_max=hp_max,
            gold=GameParser.parse_gold(html),
            level=GameParser.parse_level(html),
            xp_current=xp_cur, xp_max=xp_max,
            expedition_points=exp_cur, expedition_max=exp_max,
            dungeon_points=dng_cur, dungeon_max=dng_max,
        )

    @staticmethod
    def is_session_expired(html: str) -> bool:
        if "mod=start&submod=login" in html or "loginForm" in html:
            return True
        if re.search(r"location\.href\s*=.*login", html):
            return True
        return False

    @staticmethod
    def parse_equipment_slots(html: str) -> dict[int, InventoryItem]:
        soup = GameParser._soup(html)
        slots: dict[int, InventoryItem] = {}
        for slot_id in range(1, 12):
            slot_el = soup.select_one(f'[data-slot="{slot_id}"] .ui-draggable, #char_slot_{slot_id} .inventory_item')
            if slot_el:
                item = GameParser._parse_item_element(slot_el)
                if item:
                    slots[slot_id] = item
        return slots

    @staticmethod
    def parse_npc_shop_items(html: str) -> list[InventoryItem]:
        soup = GameParser._soup(html)
        items = []
        for item_el in soup.select(".shop_item, .market_item"):
            item = GameParser._parse_item_element(item_el)
            if item:
                items.append(item)
        return items

    @staticmethod
    def parse_sell_price(html: str) -> int:
        m = re.search(r'(?:sell|price|gold)\s*:?\s*(\d+)', html, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    @staticmethod
    def parse_work_cooldown(html: str) -> int:
        m = re.search(r"var\s+workTimer\s*=\s*(\d+)", html)
        if m:
            return int(m.group(1))
        m = re.search(r"workFinishTime\s*=\s*(\d+)", html)
        if m:
            import time
            finish = int(m.group(1))
            remaining = finish - int(time.time())
            return max(0, remaining)
        return GameParser.parse_cooldown(html)

    @staticmethod
    def parse_work_status(html: str) -> dict:
        status = {"working": False, "cooldown": 0}
        if re.search(r"(?:already\s+working|Bereits\s+am\s+Arbeiten|workTimer|workFinishTime)", html, re.IGNORECASE):
            status["working"] = True
            status["cooldown"] = GameParser.parse_work_cooldown(html)
        if re.search(r"(?:Keine Arbeit|not working|Start work|Arbeit beginnen)", html, re.IGNORECASE):
            status["working"] = False
        return status

    @staticmethod
    def parse_package_items(html: str) -> list[PackageItem]:
        soup = GameParser._soup(html)
        items: list[PackageItem] = []
        for inp in soup.select('input[name="packages[]"]'):
            pkg_id = inp.get("value", "")
            if not pkg_id:
                continue
            parent = inp.find_parent("div") or inp.find_parent("tr")
            name = ""
            quality = 0
            if parent:
                name_el = parent.select_one(".item_name, .package_name")
                if name_el:
                    name = name_el.get_text(strip=True)
                qual_m = re.search(r'quality[_-]?(\d+)', str(parent))
                if qual_m:
                    quality = int(qual_m.group(1))
            items.append(PackageItem(package_id=pkg_id, name=name, quality=quality))

        for item_el in soup.select(".packageItem, .package_item"):
            item_id = item_el.get("data-item-id", item_el.get("data-id", ""))
            if not item_id:
                continue
            if any(p.package_id == item_id for p in items):
                continue
            name = ""
            quality = 0
            name_el = item_el.select_one(".item_name, .package_name")
            if name_el:
                name = name_el.get_text(strip=True)
            qual_m = re.search(r'quality[_-]?(\d+)', str(item_el))
            if qual_m:
                quality = int(qual_m.group(1))
            items.append(PackageItem(package_id=str(item_id), name=name, quality=quality))
        return items

    @staticmethod
    def parse_dungeon_points(html: str) -> tuple[int, int]:
        soup = GameParser._soup(html)
        cur_el = soup.select_one("#dungeonpoints_value_point")
        max_el = soup.select_one("#dungeonpoints_value_pointmax")
        if cur_el and max_el:
            cur = re.search(r"\d+", cur_el.get_text(strip=True))
            mx = re.search(r"\d+", max_el.get_text(strip=True))
            if cur and mx:
                return int(cur.group()), int(mx.group())
        dp_val = soup.select_one("#dungeonpoints_value")
        if dp_val:
            text = dp_val.get_text(strip=True)
            m = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 0, 0

    @staticmethod
    def parse_arena_cooldown(html: str) -> int:
        m = re.search(r"var\s+arenaTimer\s*=\s*(\d+)", html)
        if m:
            return int(m.group(1))
        m = re.search(r"arenaCooldown\s*[=:]\s*(\d+)", html)
        if m:
            return int(m.group(1))
        return GameParser.parse_cooldown(html)

    @staticmethod
    def parse_inventory_free_slot(html: str, bag_id: int = 512) -> tuple[int, int] | None:
        soup = GameParser._soup(html)
        occupied: set[tuple[int, int]] = set()
        for item_el in soup.select(f'[data-bag="{bag_id}"] .ui-draggable, .inventory_item'):
            bag = int(item_el.get("data-bag", 0))
            if bag == bag_id:
                x = int(item_el.get("data-x", 0))
                y = int(item_el.get("data-y", 0))
                occupied.add((x, y))
        for y in range(1, 9):
            for x in range(1, 9):
                if (x, y) not in occupied:
                    return (x, y)
        return None

    @staticmethod
    def parse_npc_shop_food(html: str) -> list[InventoryItem]:
        soup = GameParser._soup(html)
        items: list[InventoryItem] = []
        for item_el in soup.select(".shop_item, .market_item, .ui-draggable"):
            item = GameParser._parse_item_element(item_el)
            if item and item.is_food:
                items.append(item)
        for buy_link in soup.select("a[href*='buyItemId'], a[href*='submod=buyItem']"):
            href = buy_link.get("href", "")
            m = re.search(r"buyItemId=(\d+)", href)
            if not m:
                continue
            item_id = m.group(1)
            if any(i.item_id == item_id for i in items):
                continue
            parent = buy_link.find_parent("div") or buy_link.find_parent("tr")
            if parent:
                text = parent.get_text(strip=True).lower()
                if any(kw in text for kw in ("food", "heal", "bread", "fish", "meat", "hp")):
                    items.append(InventoryItem(
                        item_id=item_id, name="Food", is_food=True, heal_amount=0
                    ))
        return items
