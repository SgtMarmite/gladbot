import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestSessionEndpoints:
    def test_session_status_disconnected(self, client):
        resp = client.get("/api/session/status")
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    def test_stats_not_connected(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestModuleEndpoints:
    def test_list_modules(self, client):
        resp = client.get("/api/modules")
        assert resp.status_code == 200
        modules = resp.json()
        assert len(modules) == 10
        names = {m["name"] for m in modules}
        assert "inventory" in names
        assert "equipment" in names
        assert "training" in names

    def test_update_module(self, client):
        resp = client.put("/api/modules/inventory", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["module"]["enabled"] is True

    def test_update_module_config(self, client):
        resp = client.put("/api/modules/expedition", json={"config": {"location": 2, "stage": 3}})
        assert resp.status_code == 200
        module = resp.json()["module"]
        assert module["config"]["location"] == 2
        assert module["config"]["stage"] == 3

    def test_update_nonexistent_module(self, client):
        resp = client.put("/api/modules/nonexistent", json={"enabled": True})
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestBotEndpoints:
    def test_bot_status(self, client):
        resp = client.get("/api/bot/status")
        assert resp.status_code == 200
        assert resp.json()["running"] is False

    def test_bot_start_not_connected(self, client):
        resp = client.post("/api/bot/start")
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_bot_stop(self, client):
        resp = client.post("/api/bot/stop")
        assert resp.status_code == 200
        assert resp.json()["running"] is False


class TestStaticFiles:
    def test_index_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "GLADBOT" in resp.text
