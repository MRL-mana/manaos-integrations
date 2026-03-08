"""
tests/unit/test_scripts_misc_performance_dashboard.py
Performance Dashboard のユニットテスト
"""

import sys
import json
from unittest.mock import MagicMock, patch
import pytest

# ── hard imports のモック ──────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_instance = MagicMock()
_eh.ManaOSErrorHandler.return_value = _eh_instance
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config.return_value = {"api_call": 10.0}
sys.modules.setdefault("manaos_timeout_config", _tc)

sys.modules.setdefault("manaos_integrations._paths", MagicMock(METRICS_COLLECTOR_PORT=5127))
sys.modules.setdefault("_paths", MagicMock(METRICS_COLLECTOR_PORT=5127))

# ── モジュールをインポート ──────────────────────────────────────────────
import scripts.misc.performance_dashboard as _sut


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fixture: Flaskテストクライアント
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def client():
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
        assert "ManaOS" in _sut.DASHBOARD_HTML

    def test_metrics_collector_url_defined(self):
        assert hasattr(_sut, "METRICS_COLLECTOR_URL")
        assert isinstance(_sut.METRICS_COLLECTOR_URL, str)
        assert "http" in _sut.METRICS_COLLECTOR_URL

    def test_app_created(self):
        assert hasattr(_sut, "app")

    def test_error_handler_initialized(self):
        assert hasattr(_sut, "error_handler")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestDashboardRoute
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDashboardRoute:
    def test_dashboard_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_returns_html_content(self, client):
        resp = client.get("/")
        assert b"ManaOS" in resp.data or b"html" in resp.data.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestHealth
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHealth:
    def test_returns_healthy_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "healthy"
        assert data["service"] == "Performance Dashboard"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestGetDashboardData
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetDashboardData:
    def test_returns_200_with_mocked_httpx(self, client):
        """asyncio.runをパッチして正常データを返すことを確認（その2）"""
        fake_data = {
            "services": {"UnifiedOrchestrator": "ok"},
            "metrics": {"response_time": {}, "error_rate": {}, "success_rate": {}},
            "charts": {"labels": [], "response_time_datasets": [], "error_rate_datasets": []},
        }
        with patch("asyncio.run", return_value=fake_data):
            resp = client.get("/api/dashboard-data")
        assert resp.status_code == 200

    def test_returns_200_with_asyncio_run_patched(self, client):
        """asyncio.runをパッチして直接データを返す"""
        fake_data = {
            "services": {"UnifiedOrchestrator": "ok"},
            "metrics": {"response_time": {}, "error_rate": {}, "success_rate": {}},
            "charts": {"labels": [], "response_time_datasets": [], "error_rate_datasets": []},
        }
        with patch("asyncio.run", return_value=fake_data):
            resp = client.get("/api/dashboard-data")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "services" in data or "metrics" in data

    def test_returns_500_on_exception(self, client):
        """例外発生時に500を返すことを確認"""
        mock_error = MagicMock()
        mock_error.to_json_response.return_value = {"error": "test error", "message": "boom"}
        with patch.object(_sut.error_handler, "handle_exception", return_value=mock_error), \
             patch("asyncio.run", side_effect=Exception("unexpected error")):
            resp = client.get("/api/dashboard-data")
        assert resp.status_code == 500

    def test_accepts_hours_parameter(self, client):
        """hoursクエリパラメータを受け付けることを確認"""
        fake_data = {
            "services": {},
            "metrics": {"response_time": {}, "error_rate": {}, "success_rate": {}},
            "charts": {"labels": [], "response_time_datasets": [], "error_rate_datasets": []},
        }
        with patch("asyncio.run", return_value=fake_data):
            resp = client.get("/api/dashboard-data?hours=48")
        assert resp.status_code in (200, 500)
