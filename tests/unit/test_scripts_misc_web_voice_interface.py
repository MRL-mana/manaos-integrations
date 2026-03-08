"""tests/unit/test_scripts_misc_web_voice_interface.py

web_voice_interface.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.web_voice_interface as _mod


class TestExecuteCommand:
    def test_success_returns_success_status(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"execution_id": "exec-123", "result": "ok"}
        monkeypatch.setattr(_mod.httpx, "post", lambda *a, **kw: mock_resp)

        result = _mod.execute_command("テスト")
        assert result["status"] == "success"
        assert result["execution_id"] == "exec-123"

    def test_http_error_returns_error_status(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.httpx, "post", lambda *a, **kw: mock_resp)

        result = _mod.execute_command("テスト")
        assert result["status"] == "error"
        assert "error" in result

    def test_connection_error_returns_error_status(self, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise httpx.ConnectError("refused")
        monkeypatch.setattr(_mod.httpx, "post", _raise)

        result = _mod.execute_command("テスト")
        assert result["status"] == "error"
        assert "error" in result

    def test_default_user_and_source(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"execution_id": "x1"}

        def capture(url, json=None, **kw):
            captured["json"] = json
            return mock_resp

        monkeypatch.setattr(_mod.httpx, "post", capture)
        _mod.execute_command("hello")
        assert captured["json"]["metadata"]["user"] == "web_user"
        assert captured["json"]["metadata"]["source"] == "web_voice"

    def test_custom_user_and_source(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"execution_id": "x2"}

        def capture(url, json=None, **kw):
            captured["json"] = json
            return mock_resp

        monkeypatch.setattr(_mod.httpx, "post", capture)
        _mod.execute_command("test", user="alice", source="api")
        assert captured["json"]["metadata"]["user"] == "alice"
        assert captured["json"]["metadata"]["source"] == "api"


class TestFlaskRoutes:
    @pytest.fixture
    def client(self):
        _mod.app.config["TESTING"] = True
        with _mod.app.test_client() as c:
            yield c

    def test_health_endpoint(self, client, monkeypatch):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"

    def test_status_endpoint_when_orchestrator_down(self, client, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise httpx.ConnectError("refused")
        monkeypatch.setattr(_mod.httpx, "get", _raise)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["orchestrator_status"] == "down"
