"""Tests for scripts/misc/portal_integration_api.py"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ── top-level dependency mocks ────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# manaos_error_handler
_err_instance = MagicMock()
_err_response = {"error": "mocked error", "category": "SYSTEM", "severity": "medium"}
_err_obj = MagicMock()
_err_obj.to_json_response.return_value = _err_response
_err_instance.handle_exception.return_value = _err_obj
_eh_mod = MagicMock()
_eh_mod.ManaOSErrorHandler.return_value = _err_instance
_eh_mod.ErrorCategory = MagicMock()
_eh_mod.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh_mod)

# manaos_timeout_config
_tc_mod = MagicMock()
_tc_mod.get_timeout_config.return_value = MagicMock(get=MagicMock(return_value=10.0))
sys.modules.setdefault("manaos_timeout_config", _tc_mod)

# manaos_config_validator
_cv_mod = MagicMock()
_cv_mod.ConfigValidator = MagicMock()
sys.modules.setdefault("manaos_config_validator", _cv_mod)

# _paths
_paths_mod = MagicMock()
_paths_mod.AUTONOMY_SYSTEM_PORT = 5100
_paths_mod.MRL_MEMORY_PORT = 5101
_paths_mod.ORCHESTRATOR_PORT = 5106
_paths_mod.TASK_QUEUE_PORT = 5102
sys.modules["_paths"] = _paths_mod

# httpx.TimeoutError compatibility patch (some versions use TimeoutException)
import httpx as _httpx
if not hasattr(_httpx, "TimeoutError"):
    _httpx.TimeoutError = _httpx.TimeoutException  # type: ignore[attr-defined]

# ── import SUT ────────────────────────────────────────────────────────
_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import scripts.misc.portal_integration_api as _sut
from scripts.misc.portal_integration_api import app

app.config["TESTING"] = True


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_cache():
    _sut._idempotency_cache.clear()
    _sut._inflight.clear()
    yield
    _sut._idempotency_cache.clear()
    _sut._inflight.clear()


def _make_httpx_response(status_code=200, json_data=None, text=""):
    """Build a mock httpx Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}
    mock_resp.text = text
    return mock_resp


# ══════════════════════════════════════════════════════════════════════
class TestPureFunctions:
    def test_idempotency_key_uses_provided_key(self):
        data = {"idempotency_key": "mykey123", "text": "hello"}
        assert _sut._idempotency_key(data, "hello") == "mykey123"

    def test_idempotency_key_derives_from_text(self):
        data = {"text": "hello"}
        key = _sut._idempotency_key(data, "hello")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_idempotency_key_different_texts_different_keys(self):
        k1 = _sut._idempotency_key({}, "textA")
        k2 = _sut._idempotency_key({}, "textB")
        assert k1 != k2

    def test_get_cached_response_returns_none_when_missing(self):
        assert _sut._get_cached_response("no_such_key") is None

    def test_store_and_get_cached_response(self):
        _sut._store_cached_response("k1", {"result": "ok"})
        result = _sut._get_cached_response("k1")
        assert result == {"result": "ok"}

    def test_expired_cache_returns_none(self):
        with patch("scripts.misc.portal_integration_api.time") as mt:
            # Store at time 100, set IDEMPOTENCY_TTL_SEC=10, so expiry=110
            mt.time.return_value = 100.0
            _sut._store_cached_response("expired_k", {"data": 1})
            # Now advance time past expiry
            mt.time.return_value = 115.0
            result = _sut._get_cached_response("expired_k")
        assert result is None

    def test_generate_portal_trace_id_format(self):
        tid = _sut._generate_portal_trace_id()
        assert tid.startswith("portal_")


# ══════════════════════════════════════════════════════════════════════
class TestHealthEndpoint:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_returns_healthy_status(self, client):
        body = json.loads(client.get("/health").data)
        assert body["status"] == "healthy"


# ══════════════════════════════════════════════════════════════════════
class TestExecuteTask:
    def test_400_when_no_text(self, client):
        r = client.post("/api/execute", json={})
        assert r.status_code == 400

    def test_proxies_to_orchestrator_success(self, client):
        mock_resp = _make_httpx_response(200, {"result": "done", "success": True})
        with patch("scripts.misc.portal_integration_api.httpx.post", return_value=mock_resp):
            r = client.post("/api/execute", json={"text": "hello"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["result"] == "done"

    def test_504_on_timeout(self, client):
        import httpx
        with patch("scripts.misc.portal_integration_api.httpx.post",
                   side_effect=httpx.TimeoutError("timeout")):  # type: ignore[attr-defined]
            r = client.post("/api/execute", json={"text": "slow query"})
        assert r.status_code == 504

    def test_500_on_generic_exception(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.post",
                   side_effect=RuntimeError("network error")):
            r = client.post("/api/execute", json={"text": "query"})
        assert r.status_code == 500

    def test_uses_query_as_fallback(self, client):
        mock_resp = _make_httpx_response(200, {"result": "ok"})
        with patch("scripts.misc.portal_integration_api.httpx.post", return_value=mock_resp):
            r = client.post("/api/execute", json={"query": "use query key"})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
class TestAskOrchestrator:
    def test_400_when_no_query(self, client):
        r = client.post("/api/ask_orchestrator", json={})
        assert r.status_code == 400

    def test_returns_orchestrator_response(self, client):
        mock_resp = _make_httpx_response(200, {"answer": "42"})
        with patch("scripts.misc.portal_integration_api.httpx.post", return_value=mock_resp):
            r = client.post("/api/ask_orchestrator", json={"query": "What is life?"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["answer"] == "42"

    def test_504_on_timeout(self, client):
        import httpx
        with patch("scripts.misc.portal_integration_api.httpx.post",
                   side_effect=httpx.TimeoutError("slow")):  # type: ignore[attr-defined]
            r = client.post("/api/ask_orchestrator", json={"query": "slow"})
        assert r.status_code == 504

    def test_idempotency_caching(self, client):
        mock_resp = _make_httpx_response(200, {"answer": "cached"})
        with patch("scripts.misc.portal_integration_api.httpx.post",
                   return_value=mock_resp) as mock_post:
            r1 = client.post("/api/ask_orchestrator",
                             json={"query": "same query", "idempotency_key": "idem_k"})
            r2 = client.post("/api/ask_orchestrator",
                             json={"query": "same query", "idempotency_key": "idem_k"})
        # Second call should use cache (post called only once)
        assert mock_post.call_count == 1
        assert r1.status_code == 200
        assert r2.status_code == 200


# ══════════════════════════════════════════════════════════════════════
class TestOrchestratorStats:
    def test_503_when_metrics_unavailable(self, client):
        with patch.object(_sut, "ORCHESTRATOR_METRICS_AVAILABLE", new=False):
            r = client.get("/api/orchestrator/stats")
        assert r.status_code == 503

    def test_returns_stats_when_available(self, client):
        mock_stats = {"total": 100, "success": 90}
        with patch.object(_sut, "ORCHESTRATOR_METRICS_AVAILABLE", new=True), \
             patch.object(_sut, "get_orchestrator_stats", return_value=mock_stats):
            r = client.get("/api/orchestrator/stats")
        assert r.status_code == 200
        assert json.loads(r.data) == mock_stats


# ══════════════════════════════════════════════════════════════════════
class TestModeEndpoints:
    def test_get_mode_returns_from_upstream(self, client):
        mock_resp = _make_httpx_response(200, {"mode": "manual"})
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/mode")
        assert r.status_code == 200
        assert json.loads(r.data)["mode"] == "manual"

    def test_get_mode_fallback_on_error(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.get",
                   side_effect=RuntimeError("conn refused")):
            r = client.get("/api/mode")
        assert r.status_code == 200
        assert json.loads(r.data)["mode"] == "auto"

    def test_set_mode_400_when_missing(self, client):
        r = client.post("/api/mode", json={})
        assert r.status_code == 400

    def test_set_mode_proxies_success(self, client):
        mock_resp = _make_httpx_response(200, {"mode": "manual", "success": True})
        with patch("scripts.misc.portal_integration_api.httpx.post", return_value=mock_resp):
            r = client.post("/api/mode", json={"mode": "manual"})
        assert r.status_code == 200

    def test_set_mode_500_on_exception(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.post",
                   side_effect=RuntimeError("fail")):
            r = client.post("/api/mode", json={"mode": "auto"})
        assert r.status_code == 500


# ══════════════════════════════════════════════════════════════════════
class TestCostEndpoint:
    def test_returns_cost_data(self, client):
        mock_resp = _make_httpx_response(200, {"cost_usd": 0.05})
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/cost?days=7")
        assert r.status_code == 200
        assert json.loads(r.data)["cost_usd"] == 0.05

    def test_returns_error_on_exception(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.get",
                   side_effect=RuntimeError("failed")):
            r = client.get("/api/cost")
        assert r.status_code == 500


# ══════════════════════════════════════════════════════════════════════
class TestQueueStatus:
    def test_returns_queue_info(self, client):
        mock_resp = _make_httpx_response(200, {"queued": 3, "running": 1})
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/queue/status")
        assert r.status_code == 200

    def test_error_returned_on_exception(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.get",
                   side_effect=ConnectionError("down")):
            r = client.get("/api/queue/status")
        assert r.status_code == 500


# ══════════════════════════════════════════════════════════════════════
class TestHistoryEndpoint:
    def test_returns_history_list(self, client):
        mock_resp = _make_httpx_response(200, {"history": [], "total": 0})
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/history?limit=5")
        assert r.status_code == 200

    def test_error_on_exception(self, client):
        with patch("scripts.misc.portal_integration_api.httpx.get",
                   side_effect=RuntimeError("error")):
            r = client.get("/api/history")
        assert r.status_code == 500


# ══════════════════════════════════════════════════════════════════════
class TestExecutionEndpoint:
    def test_returns_execution_data(self, client):
        mock_resp = _make_httpx_response(200, {"execution_id": "abc", "status": "done"})
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/execution/abc")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["execution_id"] == "abc"

    def test_proxies_error_status(self, client):
        mock_resp = _make_httpx_response(404, {}, text="not found")
        with patch("scripts.misc.portal_integration_api.httpx.get", return_value=mock_resp):
            r = client.get("/api/execution/badid")
        assert r.status_code == 404
