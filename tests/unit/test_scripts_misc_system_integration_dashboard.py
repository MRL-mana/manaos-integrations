"""
tests/unit/test_scripts_misc_system_integration_dashboard.py
System Integration Dashboard のユニットテスト
"""

import sys
import json
from unittest.mock import MagicMock, patch
import pytest

# ── 問題のある依存だけモック（flask/flask_cors は実物を使う） ──────────
sys.modules.setdefault("manaos_integration_orchestrator", MagicMock())
sys.modules.setdefault("manaos_integrations._paths", MagicMock(PORTAL_INTEGRATION_PORT=5108))
sys.modules.setdefault("_paths", MagicMock(PORTAL_INTEGRATION_PORT=5108))

# ── モジュールをインポート ──────────────────────────────────────────────
import scripts.misc.system_integration_dashboard as _sut


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fixture: Flask test client
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def client():
    """実際のFlaskテストクライアント"""
    _sut.app.config["TESTING"] = True
    with _sut.app.test_client() as c:
        yield c


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestModuleLevel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestModuleLevel:
    def test_dashboard_html_defined(self):
        assert hasattr(_sut, "DASHBOARD_HTML")
        assert isinstance(_sut.DASHBOARD_HTML, str)
        assert len(_sut.DASHBOARD_HTML) > 100

    def test_orchestrator_available_flag_exists(self):
        assert hasattr(_sut, "ORCHESTRATOR_AVAILABLE")
        assert isinstance(_sut.ORCHESTRATOR_AVAILABLE, bool)

    def test_httpx_available_flag_exists(self):
        assert hasattr(_sut, "HTTPX_AVAILABLE")
        assert isinstance(_sut.HTTPX_AVAILABLE, bool)

    def test_portal_url_defined(self):
        assert hasattr(_sut, "PORTAL_URL")
        assert isinstance(_sut.PORTAL_URL, str)
        assert "http" in _sut.PORTAL_URL

    def test_app_created(self):
        assert hasattr(_sut, "app")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestInitOrchestrator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInitOrchestrator:
    def test_returns_none_when_not_available(self):
        original = _sut.ORCHESTRATOR_AVAILABLE
        _sut.ORCHESTRATOR_AVAILABLE = False
        _sut.orchestrator = None
        result = _sut.init_orchestrator()
        _sut.ORCHESTRATOR_AVAILABLE = original
        assert result is None

    def test_initializes_orchestrator_when_available(self):
        _sut.orchestrator = None
        _sut.ORCHESTRATOR_AVAILABLE = True
        mock_orch_instance = MagicMock()
        mock_class = MagicMock(return_value=mock_orch_instance)
        _sut.ManaOSIntegrationOrchestrator = mock_class

        result = _sut.init_orchestrator()
        assert result == mock_orch_instance
        _sut.orchestrator = None

    def test_reuses_existing_orchestrator(self):
        mock_existing = MagicMock()
        _sut.orchestrator = mock_existing
        _sut.ORCHESTRATOR_AVAILABLE = True

        result = _sut.init_orchestrator()
        assert result is mock_existing
        _sut.orchestrator = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestDashboardRoute (実Flaskクライアント)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDashboardRoute:
    def test_dashboard_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_returns_html(self, client):
        resp = client.get("/")
        assert b"ManaOS" in resp.data or b"html" in resp.data.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestGetStatus
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetStatus:
    def test_returns_503_when_no_orchestrator(self, client):
        _sut.orchestrator = None
        _sut.ORCHESTRATOR_AVAILABLE = False
        resp = client.get("/api/status")
        assert resp.status_code == 503
        data = json.loads(resp.data)
        assert "error" in data

    def test_returns_status_when_orchestrator_available(self, client):
        mock_orch = MagicMock()
        mock_orch.get_comprehensive_status.return_value = {
            "timestamp": "2024-01-01",
            "services": {},
            "orchestrator": {},
        }
        _sut.orchestrator = None
        _sut.ORCHESTRATOR_AVAILABLE = True
        _sut.ManaOSIntegrationOrchestrator = MagicMock(return_value=mock_orch)
        resp = client.get("/api/status")
        _sut.orchestrator = None
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "timestamp" in data or "services" in data

    def test_returns_500_on_exception(self, client):
        mock_orch = MagicMock()
        mock_orch.get_comprehensive_status.side_effect = RuntimeError("boom")
        _sut.orchestrator = None
        _sut.ORCHESTRATOR_AVAILABLE = True
        _sut.ManaOSIntegrationOrchestrator = MagicMock(return_value=mock_orch)
        resp = client.get("/api/status")
        _sut.orchestrator = None
        assert resp.status_code == 500
        data = json.loads(resp.data)
        assert "error" in data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestHealth
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHealth:
    def test_returns_healthy_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "healthy"
        assert data["service"] == "System Integration Dashboard"
        assert "timestamp" in data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestGetOrchestratorStats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetOrchestratorStats:
    def test_returns_503_when_httpx_not_available(self, client):
        _sut.HTTPX_AVAILABLE = False
        resp = client.get("/api/orchestrator/stats")
        _sut.HTTPX_AVAILABLE = True
        assert resp.status_code == 503

    def test_proxies_portal_response_on_success(self, client):
        import httpx as real_httpx
        _sut.HTTPX_AVAILABLE = True
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": {"ok": 5}, "updated_at": "2024-01-01"}
        with patch("httpx.get", return_value=mock_response):
            resp = client.get("/api/orchestrator/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "status" in data

    def test_returns_503_on_exception(self, client):
        _sut.HTTPX_AVAILABLE = True
        with patch("httpx.get", side_effect=Exception("connection refused")):
            resp = client.get("/api/orchestrator/stats")
        assert resp.status_code == 503
        data = json.loads(resp.data)
        assert "error" in data
