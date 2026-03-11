"""
tests/unit/test_scripts_misc_realtime_dashboard.py
Unit tests for scripts/misc/realtime_dashboard.py
"""
import sys
import types
from typing import Any, cast
import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub hard dependencies before module import
# ---------------------------------------------------------------------------

# flask が MagicMock に汚染されていた場合のみ本物に差し替える
# (collection order: content_generation_loop(c) < realtime_dashboard(r) なので
#  content_generation_loop の setdefault("flask", MagicMock()) が先に実行される)
_cur_flask = sys.modules.get("flask")
if (
    _cur_flask is None
    or not hasattr(_cur_flask, "Flask")
    or isinstance(_cur_flask.Flask, MagicMock)
):
    # MagicMock 汚染を除去して本物をロード
    sys.modules.pop("flask", None)
    sys.modules.pop("flask_cors", None)
    import flask as _real_flask  # noqa: F401

# unified_api_server
# 後続テスト（e2e / performance / integration）への汚染を防ぐため
# 上書き前に元の値を保存し、SUT import 後に即座に復元する。
_uas_original: Any = sys.modules.get("unified_api_server")
_uas_mock: Any = cast(Any, types.ModuleType("unified_api_server"))
_fake_integrations: dict[str, Any] = {}
_uas_mock.initialize_integrations = MagicMock()
_uas_mock.integrations = _fake_integrations
sys.modules["unified_api_server"] = _uas_mock  # SUT import のために一時的に設定

# flask_socketio
_fsi: Any = cast(Any, types.ModuleType("flask_socketio"))
_socketio_instance = MagicMock()
_fsi.SocketIO = MagicMock(return_value=_socketio_instance)
_fsi.emit = MagicMock()
sys.modules.setdefault("flask_socketio", _fsi)

# manaos_service_bridge (optional, already guarded by try/except in source)
_msb: Any = cast(Any, types.ModuleType("manaos_service_bridge"))
_msb.ManaOSServiceBridge = MagicMock(side_effect=ImportError("stub"))
sys.modules.setdefault("manaos_service_bridge", _msb)

# ai_agent_autonomous (optional, guarded by try/except)
_aaa: Any = cast(Any, types.ModuleType("ai_agent_autonomous"))
_aaa.AutonomousAgent = MagicMock(side_effect=ImportError("stub"))
sys.modules.setdefault("ai_agent_autonomous", _aaa)

# realtime_dashboard を強制再ロード（flask がモック状態でロードされていた場合を修正）
sys.modules.pop("scripts.misc.realtime_dashboard", None)
import scripts.misc.realtime_dashboard as _sut  # noqa: E402, F811

# SUT が unified_api_server のモックを使って初期化されたので、
# sys.modules["unified_api_server"] を元の値に戻す（他テストへの汚染防止）。
# _sut.integrations は既に _fake_integrations への参照を持っているため、
# sys.modules のエントリを戻しても _sut の動作には影響しない。
if _uas_original is not None:
    sys.modules["unified_api_server"] = _uas_original
else:
    sys.modules.pop("unified_api_server", None)


@pytest.fixture(autouse=True)
def reset_globals():
    """Isolate bridge/agent per test."""
    orig_bridge = _sut.bridge
    orig_agent = _sut.agent
    _sut.bridge = None
    _sut.agent = None
    # reset integrations dict
    _uas_mock.integrations.clear()
    yield
    _sut.bridge = orig_bridge
    _sut.agent = orig_agent


@pytest.fixture()
def client():
    _sut.app.config["TESTING"] = True
    with _sut.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Module-level
# ---------------------------------------------------------------------------
class TestModuleLevel:
    def test_app_exists(self):
        assert _sut.app is not None

    def test_socketio_created(self):
        assert _sut.socketio is not None

    def test_html_template_defined(self):
        assert "DASHBOARD_HTML" in dir(_sut)
        assert "<html>" in _sut.DASHBOARD_HTML

    def test_bridge_is_none_after_reset(self):
        assert _sut.bridge is None

    def test_agent_is_none_after_reset(self):
        assert _sut.agent is None


# ---------------------------------------------------------------------------
# GET / — dashboard()
# ---------------------------------------------------------------------------
class TestDashboardRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/")
        assert b"ManaOS" in resp.data

    def test_content_type_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.content_type


# ---------------------------------------------------------------------------
# GET /api/dashboard/status — get_status()
# ---------------------------------------------------------------------------
class TestGetStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/dashboard/status")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_has_required_keys(self, client):
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert "integrations" in data
        assert "manaos_services" in data
        assert "agent" in data
        assert "timestamp" in data

    def test_integrations_empty_when_no_integrations(self, client):
        # _fake_integrations is empty (reset_globals clears it)
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["integrations"] == {}

    def test_integrations_with_is_available(self, client):
        mock_integration = MagicMock()
        mock_integration.is_available.return_value = True
        _uas_mock.integrations["test_service"] = mock_integration
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert "test_service" in data["integrations"]
        assert data["integrations"]["test_service"] is True

    def test_integrations_without_is_available(self, client):
        # integration without is_available attribute → False
        plain_obj = object()
        _uas_mock.integrations["plain"] = plain_obj
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["integrations"]["plain"] is False

    def test_bridge_check_called_when_present(self, client):
        mock_bridge = MagicMock()
        mock_bridge.check_manaos_services.return_value = {"svc": True}
        _sut.bridge = mock_bridge
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["manaos_services"] == {"svc": True}
        mock_bridge.check_manaos_services.assert_called_once()

    def test_bridge_error_returns_empty_manaos(self, client):
        mock_bridge = MagicMock()
        mock_bridge.check_manaos_services.side_effect = RuntimeError("fail")
        _sut.bridge = mock_bridge
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["manaos_services"] == {}

    def test_agent_status_called_when_present(self, client):
        mock_agent = MagicMock()
        mock_agent.get_status.return_value = {"state": "idle"}
        _sut.agent = mock_agent
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["agent"] == {"state": "idle"}

    def test_agent_error_returns_empty_agent(self, client):
        mock_agent = MagicMock()
        mock_agent.get_status.side_effect = Exception("agent crash")
        _sut.agent = mock_agent
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert data["agent"] == {}

    def test_timestamp_is_string(self, client):
        resp = client.get("/api/dashboard/status")
        data = resp.get_json()
        assert isinstance(data["timestamp"], str)
