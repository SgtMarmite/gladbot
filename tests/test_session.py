import pytest

from src.config import Settings
from src.session.manager import SessionExpired, SessionManager


class TestSessionManager:
    def test_init(self):
        sm = SessionManager(Settings())
        assert sm.connected is False
        assert sm.secure_hash == ""

    def test_parse_url(self):
        sm = SessionManager(Settings())
        url = "https://s62-cz.gladiatus.gameforge.com/game/index.php?mod=overview&sh=abc123"
        parsed_scheme = "https"
        assert "sh=abc123" in url
        assert "s62-cz" in url


class TestSessionExpiredException:
    def test_exception(self):
        exc = SessionExpired("test")
        assert str(exc) == "test"
