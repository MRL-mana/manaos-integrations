"""
Unit tests for scripts/misc/prometheus_integration.py
"""
import sys
import types
from unittest.mock import MagicMock, patch, call

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────

# unified_logging
_ul = types.ModuleType("unified_logging")
_ul.get_service_logger = MagicMock(return_value=MagicMock())  # type: ignore
sys.modules["unified_logging"] = _ul

# prometheus_client — Counter / Histogram / Gauge / generate_latest / CONTENT_TYPE_LATEST
_counter_inst = MagicMock()
_hist_inst = MagicMock()
_gauge_inst = MagicMock()

_pc_mod = types.ModuleType("prometheus_client")
_pc_mod.Counter = MagicMock(return_value=_counter_inst)  # type: ignore
_pc_mod.Histogram = MagicMock(return_value=_hist_inst)  # type: ignore
_pc_mod.Gauge = MagicMock(return_value=_gauge_inst)  # type: ignore
_pc_mod.generate_latest = MagicMock(return_value=b"# HELP metrics\n")  # type: ignore
_pc_mod.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"  # type: ignore
sys.modules["prometheus_client"] = _pc_mod

import scripts.misc.prometheus_integration as pi


# ─────────────────────────────────────────────
# PROMETHEUS_AVAILABLE
# ─────────────────────────────────────────────

class TestPrometheusAvailable:
    def test_available_flag_is_true(self):
        assert pi.PROMETHEUS_AVAILABLE is True


# ─────────────────────────────────────────────
# PrometheusMetrics.__init__
# ─────────────────────────────────────────────

class TestPrometheusMetricsInit:
    def test_creates_counters(self):
        m = pi.PrometheusMetrics()
        assert m.request_count is not None
        assert m.error_count is not None

    def test_creates_histograms(self):
        m = pi.PrometheusMetrics()
        assert m.request_duration is not None
        assert m.llm_call_duration is not None

    def test_creates_gauges(self):
        m = pi.PrometheusMetrics()
        assert m.active_connections is not None
        assert m.gpu_usage is not None
        assert m.cpu_usage is not None
        assert m.memory_usage is not None
        assert m.cache_hit_rate is not None
        assert m.service_health is not None

    def test_raises_when_prometheus_unavailable(self):
        original = pi.PROMETHEUS_AVAILABLE
        pi.PROMETHEUS_AVAILABLE = False
        try:
            with pytest.raises(ImportError):
                pi.PrometheusMetrics()
        finally:
            pi.PROMETHEUS_AVAILABLE = original


# ─────────────────────────────────────────────
# PrometheusMetrics methods
# ─────────────────────────────────────────────

@pytest.fixture
def metrics():
    return pi.PrometheusMetrics()


class TestRecordRequest:
    def test_calls_inc_on_counter(self, metrics):
        metrics.record_request("GET", "/api/status", 200, 0.5)
        metrics.request_count.labels.assert_called()

    def test_calls_observe_on_histogram(self, metrics):
        metrics.record_request("POST", "/api/run", 201, 1.2)
        metrics.request_duration.labels.assert_called()

    def test_error_status_for_4xx(self, metrics):
        metrics.record_request("GET", "/fail", 400, 0.1)
        call_kwargs = metrics.request_count.labels.call_args[1]
        assert call_kwargs["status"] == "error"

    def test_success_status_for_2xx(self, metrics):
        metrics.record_request("GET", "/ok", 200, 0.1)
        call_kwargs = metrics.request_count.labels.call_args[1]
        assert call_kwargs["status"] == "success"


class TestRecordError:
    def test_calls_inc(self, metrics):
        metrics.record_error("ValueError", "svc1")
        metrics.error_count.labels.assert_called_with(error_type="ValueError", service="svc1")


class TestRecordLlmCall:
    def test_calls_observe(self, metrics):
        metrics.record_llm_call("qwen2.5", "chat", 3.0)
        metrics.llm_call_duration.labels.assert_called_with(model="qwen2.5", task_type="chat")


class TestUpdateSystemMetrics:
    def test_sets_cpu_and_memory(self, metrics):
        metrics.update_system_metrics(55.0, 8 * 1024 * 1024 * 1024)
        # Both share the same _gauge_inst mock — use assert_any_call
        metrics.cpu_usage.set.assert_any_call(55.0)
        metrics.memory_usage.set.assert_any_call(8 * 1024 * 1024 * 1024)


class TestUpdateGpuMetrics:
    def test_sets_gpu_usage(self, metrics):
        metrics.update_gpu_metrics("gpu0", 80.0)
        metrics.gpu_usage.labels.assert_called_with(gpu_id="gpu0")


class TestUpdateCacheMetrics:
    def test_sets_cache_hit_rate(self, metrics):
        metrics.update_cache_metrics(0.95)
        metrics.cache_hit_rate.set.assert_called_with(0.95)


class TestUpdateServiceHealth:
    def test_healthy_sets_1(self, metrics):
        metrics.update_service_health("svc1", True)
        rv = metrics.service_health.labels.return_value
        rv.set.assert_called_with(1)

    def test_unhealthy_sets_0(self, metrics):
        metrics.update_service_health("svc1", False)
        rv = metrics.service_health.labels.return_value
        rv.set.assert_called_with(0)


class TestGetMetrics:
    def test_returns_bytes_from_generate_latest(self, metrics):
        result = metrics.get_metrics()
        assert isinstance(result, bytes)
        _pc_mod.generate_latest.assert_called()


# ─────────────────────────────────────────────
# get_prometheus_metrics (singleton)
# ─────────────────────────────────────────────

class TestGetPrometheusMetrics:
    def test_returns_none_when_unavailable(self):
        # Reset singleton
        pi._prometheus_metrics = None
        original = pi.PROMETHEUS_AVAILABLE
        pi.PROMETHEUS_AVAILABLE = False
        try:
            result = pi.get_prometheus_metrics()
            assert result is None
        finally:
            pi.PROMETHEUS_AVAILABLE = original
            pi._prometheus_metrics = None

    def test_returns_same_instance_on_second_call(self):
        pi._prometheus_metrics = None
        try:
            m1 = pi.get_prometheus_metrics()
            m2 = pi.get_prometheus_metrics()
            assert m1 is m2
        finally:
            pi._prometheus_metrics = None


# ─────────────────────────────────────────────
# setup_prometheus_endpoint (Flask integration)
# ─────────────────────────────────────────────

class TestSetupPrometheusEndpoint:
    def test_adds_metrics_route(self):
        from flask import Flask
        app = Flask(__name__)
        m = pi.PrometheusMetrics()
        pi.setup_prometheus_endpoint(app, m)

        with app.test_client() as c:
            resp = c.get("/metrics")
        assert resp.status_code == 200
