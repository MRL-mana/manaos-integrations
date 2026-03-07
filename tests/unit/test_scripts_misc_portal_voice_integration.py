"""
Unit tests for scripts/misc/portal_voice_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

# ── mocks (before import) ─────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(
    return_value=MagicMock(user_message="err_msg", message="err_detail")
)
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"workflow_execution": 30.0})
sys.modules.setdefault("manaos_timeout_config", _tc)

# flask / flask_cors
sys.modules.setdefault("flask_cors", MagicMock())

import pytest

# ── import module ────────────────────────────────────────────────────────────
import scripts.misc.portal_voice_integration as pvi

# Use the real Flask app defined in module
app = pvi.app
app.testing = True


@pytest.fixture
def client():
    return app.test_client()


# ── TestHealth ────────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"


# ── TestVoiceExecute ──────────────────────────────────────────────────────────
class TestVoiceExecute:
    def test_execute_success(self, client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"status": "ok", "result": "done"}
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.post.return_value = mock_resp
            resp = client.post("/api/voice/execute",
                               json={"text": "照明をつけて", "user": "tester"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_execute_missing_text(self, client):
        resp = client.post("/api/voice/execute", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"
        assert "text" in data["error"]

    def test_execute_httpx_error(self, client):
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.post.side_effect = Exception("connection refused")
            resp = client.post("/api/voice/execute",
                               json={"text": "test command"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"

    def test_execute_non_200_response(self, client):
        mock_resp = MagicMock(status_code=503)
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.post.return_value = mock_resp
            resp = client.post("/api/voice/execute",
                               json={"text": "do something"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"


# ── TestSlackExecute ──────────────────────────────────────────────────────────
class TestSlackExecute:
    def test_slack_success(self, client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"status": "ok"}
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.post.return_value = mock_resp
            resp = client.post("/api/slack/execute",
                               json={"text": "status check", "user": "slack_user",
                                     "channel": "general"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_slack_missing_text(self, client):
        resp = client.post("/api/slack/execute", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"


# ── TestIntegrationsStatus ────────────────────────────────────────────────────
class TestIntegrationsStatus:
    def test_all_healthy(self, client):
        mock_resp = MagicMock(status_code=200)
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.get.return_value = mock_resp
            resp = client.get("/api/integrations/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["integrations"]["orchestrator"] == "healthy"
        assert data["integrations"]["slack_integration"] == "healthy"
        assert data["integrations"]["web_voice"] == "healthy"

    def test_all_down(self, client):
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.get.side_effect = Exception("timeout")
            resp = client.get("/api/integrations/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["integrations"]["orchestrator"] == "down"
        assert data["integrations"]["slack_integration"] == "down"
        assert data["integrations"]["web_voice"] == "down"

    def test_unhealthy_status_code(self, client):
        mock_resp = MagicMock(status_code=500)
        with patch.object(pvi, "httpx") as _httpx:
            _httpx.get.return_value = mock_resp
            resp = client.get("/api/integrations/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["integrations"]["orchestrator"] == "unhealthy"
