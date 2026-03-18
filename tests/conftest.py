from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def overview_html():
    return (FIXTURES_DIR / "overview.html").read_text()


@pytest.fixture
def quests_html():
    return (FIXTURES_DIR / "quests.html").read_text()


@pytest.fixture
def arena_html():
    return (FIXTURES_DIR / "arena.html").read_text()


@pytest.fixture
def dungeon_html():
    return (FIXTURES_DIR / "dungeon.html").read_text()


@pytest.fixture
def inventory_html():
    return (FIXTURES_DIR / "inventory.html").read_text()


@pytest.fixture
def training_html():
    return (FIXTURES_DIR / "training.html").read_text()


@pytest.fixture
def work_html():
    return (FIXTURES_DIR / "work.html").read_text()


@pytest.fixture
def work_idle_html():
    return (FIXTURES_DIR / "work_idle.html").read_text()


@pytest.fixture
def packages_html():
    return (FIXTURES_DIR / "packages.html").read_text()
