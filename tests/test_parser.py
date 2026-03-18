from src.session.parser import GameParser


class TestParseSecureHash:
    def test_from_js_var(self, overview_html):
        assert GameParser.parse_secure_hash(overview_html) == "abc123def456"

    def test_from_url_param(self):
        html = '<a href="index.php?mod=overview&sh=deadbeef01">'
        assert GameParser.parse_secure_hash(html) == "deadbeef01"

    def test_missing(self):
        assert GameParser.parse_secure_hash("<html></html>") is None


class TestParseHP:
    def test_from_bar_text(self, overview_html):
        hp_cur, hp_max = GameParser.parse_hp(overview_html)
        assert hp_cur == 80
        assert hp_max == 100

    def test_from_global_data(self):
        html = """<script>
        globalData = {};
        globalData.playerData = {};
        globalData.playerData.hpActual = 45;
        globalData.playerData.hpMax = 200;
        </script>"""
        hp_cur, hp_max = GameParser.parse_hp(html)
        assert hp_cur == 45
        assert hp_max == 200

    def test_missing(self):
        assert GameParser.parse_hp("<html></html>") == (0, 0)


class TestParseGold:
    def test_from_element(self, overview_html):
        assert GameParser.parse_gold(overview_html) == 5370

    def test_from_global_data(self):
        html = "<script>globalData.playerData.gold = 9999;</script>"
        assert GameParser.parse_gold(html) == 9999


class TestParseLevel:
    def test_from_element(self, overview_html):
        assert GameParser.parse_level(overview_html) == 12


class TestParseXP:
    def test_from_bar(self, overview_html):
        xp_cur, xp_max = GameParser.parse_xp(overview_html)
        assert xp_cur == 1500
        assert xp_max == 3000


class TestParseExpeditionPoints:
    def test_from_bar(self, overview_html):
        cur, mx = GameParser.parse_expedition_points(overview_html)
        assert cur == 3
        assert mx == 6


class TestParseCooldown:
    def test_from_js_var(self):
        html = "<script>var cooldownTimer = 120;</script>"
        assert GameParser.parse_cooldown(html) == 120

    def test_missing(self):
        assert GameParser.parse_cooldown("<html></html>") == 0


class TestParseDungeon:
    def test_dungeon_id(self, dungeon_html):
        assert GameParser.parse_dungeon_id(dungeon_html) == "7890"

    def test_dungeon_enemies(self, dungeon_html):
        enemies = GameParser.parse_dungeon_enemies(dungeon_html)
        assert len(enemies) == 4
        assert enemies[0]["position"] == 1
        assert enemies[0]["defeated"] is False
        assert enemies[1]["position"] == 2
        assert enemies[1]["defeated"] is True


class TestParseArenaOpponents:
    def test_opponents(self, arena_html):
        opponents = GameParser.parse_arena_opponents(arena_html)
        assert len(opponents) == 3
        assert opponents[0].name == "Warrior123"
        assert opponents[0].level == 10
        assert opponents[0].player_id == "4001"
        assert opponents[1].level == 50


class TestParseQuestSlots:
    def test_quest_slots(self, quests_html):
        slots = GameParser.parse_quest_slots(quests_html)
        assert len(slots) == 4
        statuses = {s.position: s.status for s in slots}
        assert statuses[1] == "finished"
        assert statuses[2] == "active"
        assert statuses[3] == "available"
        assert statuses[4] == "restartable"


class TestParseInventory:
    def test_food_items(self, inventory_html):
        foods = GameParser.parse_food_items(inventory_html, bag_id=512)
        assert len(foods) == 2
        assert foods[0].is_food is True
        assert foods[0].name == "Old Bread"
        assert foods[0].heal_amount == 25

    def test_all_items(self, inventory_html):
        items = GameParser.parse_inventory_items(inventory_html, bag_id=512)
        assert len(items) == 4

    def test_item_quality(self, inventory_html):
        items = GameParser.parse_inventory_items(inventory_html, bag_id=512)
        qualities = {i.name: i.quality for i in items}
        assert qualities["Old Bread"] == 0
        assert qualities["Green Sword"] == 1
        assert qualities["Blue Shield"] == 2

    def test_item_stats(self, inventory_html):
        items = GameParser.parse_inventory_items(inventory_html, bag_id=512)
        sword = next(i for i in items if i.name == "Green Sword")
        assert sword.stats.get("damage") == 15
        assert sword.stats.get("strength") == 5


class TestParseTrainingCosts:
    def test_costs(self, training_html):
        costs = GameParser.parse_training_costs(training_html)
        assert costs["strength"] == 120
        assert costs["dexterity"] == 150
        assert costs["agility"] == 140
        assert costs["charisma"] == 100


class TestParsePlayerStats:
    def test_full_stats(self, overview_html):
        stats = GameParser.parse_player_stats(overview_html)
        assert stats.hp_current == 80
        assert stats.hp_max == 100
        assert stats.gold == 5370
        assert stats.level == 12
        assert stats.xp_current == 1500
        assert stats.xp_max == 3000
        assert stats.expedition_points == 3
        assert stats.expedition_max == 6


class TestParseDungeonPoints:
    def test_from_elements(self, overview_html):
        cur, mx = GameParser.parse_dungeon_points(overview_html)
        assert cur == 2
        assert mx == 4

    def test_missing(self):
        assert GameParser.parse_dungeon_points("<html></html>") == (0, 0)


class TestParseWorkCooldown:
    def test_from_timer(self, work_html):
        cd = GameParser.parse_work_cooldown(work_html)
        assert cd == 14400

    def test_missing(self):
        assert GameParser.parse_work_cooldown("<html></html>") == 0


class TestParseWorkStatus:
    def test_working(self, work_html):
        status = GameParser.parse_work_status(work_html)
        assert status["working"] is True
        assert status["cooldown"] == 14400

    def test_idle(self, work_idle_html):
        status = GameParser.parse_work_status(work_idle_html)
        assert status["working"] is False


class TestParsePackageItems:
    def test_packages(self, packages_html):
        items = GameParser.parse_package_items(packages_html)
        assert len(items) == 3
        assert items[0].package_id == "5001"
        assert items[0].name == "Green Dagger"
        assert items[0].quality == 1
        assert items[1].package_id == "5002"
        assert items[1].quality == 0
        assert items[2].package_id == "5003"
        assert items[2].quality == 2

    def test_empty(self):
        assert GameParser.parse_package_items("<html></html>") == []


class TestParseArenaCooldown:
    def test_from_timer(self):
        html = "<script>var arenaTimer = 900;</script>"
        assert GameParser.parse_arena_cooldown(html) == 900

    def test_fallback_to_cooldown(self):
        html = "<script>var cooldownTimer = 600;</script>"
        assert GameParser.parse_arena_cooldown(html) == 600

    def test_missing(self):
        assert GameParser.parse_arena_cooldown("<html></html>") == 0


class TestParseInventoryFreeSlot:
    def test_finds_free(self, inventory_html):
        slot = GameParser.parse_inventory_free_slot(inventory_html, bag_id=512)
        assert slot is not None
        x, y = slot
        assert (x, y) not in {(1, 1), (2, 1), (3, 1), (1, 2)}

    def test_empty_bag(self):
        html = '<html><div data-bag="512"></div></html>'
        slot = GameParser.parse_inventory_free_slot(html, bag_id=512)
        assert slot == (1, 1)


class TestParsePlayerStatsWithDungeon:
    def test_includes_dungeon_points(self, overview_html):
        stats = GameParser.parse_player_stats(overview_html)
        assert stats.dungeon_points == 2
        assert stats.dungeon_max == 4


class TestSessionExpiry:
    def test_login_redirect(self):
        assert GameParser.is_session_expired('<a href="mod=start&submod=login">') is True

    def test_login_form(self):
        assert GameParser.is_session_expired('<form id="loginForm">') is True

    def test_valid_page(self, overview_html):
        assert GameParser.is_session_expired(overview_html) is False
