"""
tests/unit/test_scripts_misc_master_control.py
Unit tests for scripts/misc/master_control.py
"""
import sys
import types
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Prevent ultimate_integration import at module level
# ---------------------------------------------------------------------------
_ui_mock = types.ModuleType("ultimate_integration")
_ui_cls = MagicMock()
_ui_mock.UltimateIntegration = _ui_cls
sys.modules.setdefault("ultimate_integration", _ui_mock)

import importlib
import scripts.misc.master_control as _sut


@pytest.fixture(autouse=True)
def reset_system():
    """Ensure _sut.system is None for each test (isolated)."""
    orig = _sut.system
    _sut.system = None
    yield
    _sut.system = orig


@pytest.fixture()
def client():
    _sut.app.config["TESTING"] = True
    with _sut.app.test_client() as c:
        yield c


@pytest.fixture()
def mock_system():
    """Return a MagicMock that stands in for UltimateIntegration."""
    sys_mock = MagicMock()
    _sut.system = sys_mock
    yield sys_mock
    _sut.system = None


# ---------------------------------------------------------------------------
# Module-level / app setup
# ---------------------------------------------------------------------------
class TestModuleLevel:
    def test_app_exists(self):
        assert _sut.app is not None

    def test_html_template_defined(self):
        assert "MASTER_CONTROL_HTML" in dir(_sut)
        assert "<html>" in _sut.MASTER_CONTROL_HTML

    def test_system_is_none_after_reset(self):
        # autouse fixture sets system to None
        assert _sut.system is None

    def test_app_has_flask_test_client(self):
        assert callable(_sut.app.test_client)


# ---------------------------------------------------------------------------
# GET / — master_control()
# ---------------------------------------------------------------------------
class TestMasterControlRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html_content(self, client):
        resp = client.get("/")
        assert b"ManaOS" in resp.data

    def test_content_type_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.content_type


# ---------------------------------------------------------------------------
# GET /api/status — get_status()
# ---------------------------------------------------------------------------
class TestGetStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_system_none_returns_error(self, client):
        resp = client.get("/api/status")
        data = resp.get_json()
        assert "error" in data

    def test_system_none_error_message(self, client):
        resp = client.get("/api/status")
        data = resp.get_json()
        assert "not initialized" in data["error"].lower() or "error" in data

    def test_system_present_calls_get_comprehensive_status(self, client, mock_system):
        mock_system.get_comprehensive_status.return_value = {"ok": True}
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {"ok": True}
        mock_system.get_comprehensive_status.assert_called_once()

    def test_system_raises_returns_error(self, client, mock_system):
        mock_system.get_comprehensive_status.side_effect = RuntimeError("crash")
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "error" in data
        assert "crash" in data["error"]


# ---------------------------------------------------------------------------
# POST /api/execute — execute_command()
# ---------------------------------------------------------------------------
class TestExecuteCommand:
    def test_returns_200(self, client):
        resp = client.post(
            "/api/execute",
            json={"command": "test"},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_system_none_returns_error(self, client):
        resp = client.post("/api/execute", json={"command": "hello"})
        data = resp.get_json()
        assert "error" in data

    def test_system_none_error_message(self, client):
        resp = client.post("/api/execute", json={"command": "hello"})
        data = resp.get_json()
        assert "not initialized" in data["error"].lower() or "error" in data

    def test_system_present_calls_execute_intelligent_workflow(self, client, mock_system):
        mock_system.execute_intelligent_workflow.return_value = {"result": "done"}
        resp = client.post("/api/execute", json={"command": "画像生成"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {"result": "done"}
        mock_system.execute_intelligent_workflow.assert_called_once_with("画像生成")

    def test_missing_command_uses_empty_string(self, client, mock_system):
        mock_system.execute_intelligent_workflow.return_value = {"result": "empty"}
        resp = client.post("/api/execute", json={})
        assert resp.status_code == 200
        mock_system.execute_intelligent_workflow.assert_called_once_with("")

    def test_system_raises_returns_error(self, client, mock_system):
        mock_system.execute_intelligent_workflow.side_effect = ValueError("bad cmd")
        resp = client.post("/api/execute", json={"command": "broken"})
        data = resp.get_json()
        assert "error" in data
        assert "bad cmd" in data["error"]


# ---------------------------------------------------------------------------
# POST /api/full-check — full_check()
# ---------------------------------------------------------------------------
class TestFullCheck:
    def test_returns_200(self, client):
        resp = client.post("/api/full-check")
        assert resp.status_code == 200

    def test_system_none_returns_error(self, client):
        resp = client.post("/api/full-check")
        data = resp.get_json()
        assert "error" in data

    def test_system_present_calls_run_full_system_check(self, client, mock_system):
        mock_system.run_full_system_check.return_value = {"check": "pass"}
        resp = client.post("/api/full-check")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {"check": "pass"}
        mock_system.run_full_system_check.assert_called_once()

    def test_system_raises_returns_error(self, client, mock_system):
        mock_system.run_full_system_check.side_effect = Exception("check failed")
        resp = client.post("/api/full-check")
        data = resp.get_json()
        assert "error" in data
        assert "check failed" in data["error"]
