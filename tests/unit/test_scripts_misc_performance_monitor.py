"""
Unit tests for scripts/misc/performance_monitor.py
"""
import sys
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("unified_logging", _ml)

import pytest  # noqa: E402
from scripts.misc.performance_monitor import (  # noqa: E402
    PerformanceMetric,
    PerformanceMonitor,
    get_performance_monitor,
)


# ── helpers ────────────────────────────────────────────────────────────────
def make_metric(
    cpu_percent=10.0,
    memory_percent=50.0,
    disk_percent=30.0,
    response_time_avg=0.1,
    error_rate=0.0,
    **kwargs,
):
    return PerformanceMetric(
        timestamp=kwargs.get("timestamp", datetime.now()),
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
        network_sent_mb=0.0,
        network_recv_mb=0.0,
        active_connections=5,
        response_time_avg=response_time_avg,
        error_rate=error_rate,
    )


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def monitor():
    """psutil 呼び出しをスキップした PerformanceMonitor"""
    pm = PerformanceMonitor.__new__(PerformanceMonitor)
    pm.history_size = 100
    pm.metrics_history = deque(maxlen=100)
    pm.monitoring = False
    pm.monitor_task = None
    pm.last_network_stats = MagicMock(bytes_sent=0, bytes_recv=0)
    pm.last_network_time = 0.0
    return pm


# ── TestPerformanceMetric ──────────────────────────────────────────────────
class TestPerformanceMetric:
    def test_fields_accessible(self):
        m = make_metric()
        assert hasattr(m, "cpu_percent")
        assert hasattr(m, "memory_percent")
        assert hasattr(m, "disk_percent")
        assert hasattr(m, "network_sent_mb")
        assert hasattr(m, "network_recv_mb")
        assert hasattr(m, "active_connections")
        assert hasattr(m, "response_time_avg")
        assert hasattr(m, "error_rate")
        assert hasattr(m, "timestamp")

    def test_values_stored_correctly(self):
        m = make_metric(cpu_percent=42.5, memory_percent=80.0)
        assert m.cpu_percent == 42.5
        assert m.memory_percent == 80.0


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_history_size_stored(self, monitor):
        assert monitor.history_size == 100

    def test_empty_history(self, monitor):
        assert len(monitor.metrics_history) == 0

    def test_monitoring_false(self, monitor):
        assert monitor.monitoring is False


# ── TestGetCurrentMetrics ──────────────────────────────────────────────────
class TestGetCurrentMetrics:
    def test_no_history_returns_none(self, monitor):
        assert monitor.get_current_metrics() is None

    def test_returns_last_item(self, monitor):
        m1 = make_metric(cpu_percent=10.0)
        m2 = make_metric(cpu_percent=20.0)
        monitor.metrics_history.append(m1)
        monitor.metrics_history.append(m2)
        assert monitor.get_current_metrics().cpu_percent == 20.0

    def test_returns_performance_metric(self, monitor):
        monitor.metrics_history.append(make_metric())
        result = monitor.get_current_metrics()
        assert isinstance(result, PerformanceMetric)


# ── TestGetMetricsTrend ────────────────────────────────────────────────────
class TestGetMetricsTrend:
    def test_empty_history_returns_empty_dict(self, monitor):
        assert monitor.get_metrics_trend() == {}

    def test_returns_dict_with_data(self, monitor):
        monitor.metrics_history.append(make_metric())
        result = monitor.get_metrics_trend(60)
        assert isinstance(result, dict)

    def test_required_keys(self, monitor):
        monitor.metrics_history.append(make_metric())
        result = monitor.get_metrics_trend(60)
        for key in ("duration_minutes", "sample_count", "cpu", "memory",
                    "response_time", "error_rate"):
            assert key in result

    def test_sample_count_correct(self, monitor):
        for _ in range(3):
            monitor.metrics_history.append(make_metric())
        result = monitor.get_metrics_trend(60)
        assert result["sample_count"] == 3

    def test_old_metrics_excluded(self, monitor):
        old_ts = datetime.now() - timedelta(hours=2)
        monitor.metrics_history.append(make_metric(timestamp=old_ts))
        result = monitor.get_metrics_trend(60)
        assert result == {}

    def test_cpu_avg_correct(self, monitor):
        monitor.metrics_history.append(make_metric(cpu_percent=10.0))
        monitor.metrics_history.append(make_metric(cpu_percent=20.0))
        result = monitor.get_metrics_trend(60)
        assert result["cpu"]["avg"] == pytest.approx(15.0)


# ── TestCalculateTrend ─────────────────────────────────────────────────────
class TestCalculateTrend:
    def test_single_value_stable(self, monitor):
        assert monitor._calculate_trend([5.0]) == "stable"

    def test_stable_values(self, monitor):
        values = [50.0, 50.1, 49.9, 50.0]
        assert monitor._calculate_trend(values) == "stable"

    def test_increasing_trend(self, monitor):
        values = [10.0, 10.0, 90.0, 90.0]
        result = monitor._calculate_trend(values)
        assert result == "increasing"

    def test_decreasing_trend(self, monitor):
        values = [90.0, 90.0, 10.0, 10.0]
        result = monitor._calculate_trend(values)
        assert result == "decreasing"


# ── TestAnalyzePerformanceIssues ───────────────────────────────────────────
class TestAnalyzePerformanceIssues:
    def test_empty_history_returns_empty_list(self, monitor):
        assert monitor.analyze_performance_issues() == []

    def test_normal_metrics_no_issues(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(
                cpu_percent=30.0,
                memory_percent=50.0,
                response_time_avg=0.1,
                error_rate=0.0,
            ))
        assert monitor.analyze_performance_issues() == []

    def test_high_cpu_detected(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(cpu_percent=85.0))
        issues = monitor.analyze_performance_issues()
        types = [i["type"] for i in issues]
        assert "high_cpu" in types

    def test_high_memory_detected(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(memory_percent=90.0))
        issues = monitor.analyze_performance_issues()
        types = [i["type"] for i in issues]
        assert "high_memory" in types

    def test_slow_response_detected(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(response_time_avg=3.0))
        issues = monitor.analyze_performance_issues()
        types = [i["type"] for i in issues]
        assert "slow_response" in types

    def test_high_error_rate_detected(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(error_rate=0.1))
        issues = monitor.analyze_performance_issues()
        types = [i["type"] for i in issues]
        assert "high_error_rate" in types

    def test_issue_has_required_fields(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(cpu_percent=85.0))
        issues = monitor.analyze_performance_issues()
        assert issues
        issue = issues[0]
        for field in ("type", "severity", "message", "recommendation"):
            assert field in issue

    def test_cpu_critical_is_error_severity(self, monitor):
        for _ in range(5):
            monitor.metrics_history.append(make_metric(cpu_percent=95.0))
        issues = monitor.analyze_performance_issues()
        cpu_issue = next(i for i in issues if i["type"] == "high_cpu")
        assert cpu_issue["severity"] == "error"


# ── TestGetSummary ─────────────────────────────────────────────────────────
class TestGetSummary:
    def test_no_data_status(self, monitor):
        result = monitor.get_summary()
        assert result == {"status": "no_data"}

    def test_returns_dict_with_data(self, monitor):
        monitor.metrics_history.append(make_metric())
        result = monitor.get_summary()
        assert isinstance(result, dict)

    def test_required_keys(self, monitor):
        monitor.metrics_history.append(make_metric())
        result = monitor.get_summary()
        for key in ("status", "current", "issues", "history_size"):
            assert key in result

    def test_status_stopped_when_not_monitoring(self, monitor):
        monitor.metrics_history.append(make_metric())
        assert monitor.get_summary()["status"] == "stopped"

    def test_status_monitoring_when_active(self, monitor):
        monitor.monitoring = True
        monitor.metrics_history.append(make_metric())
        assert monitor.get_summary()["status"] == "monitoring"

    def test_history_size_correct(self, monitor):
        for _ in range(3):
            monitor.metrics_history.append(make_metric())
        assert monitor.get_summary()["history_size"] == 3


# ── TestGetPerformanceMonitor ──────────────────────────────────────────────
class TestGetPerformanceMonitor:
    def setup_method(self):
        import scripts.misc.performance_monitor as pm_mod
        pm_mod._performance_monitor = None  # reset singleton

    def test_returns_instance(self):
        pm = get_performance_monitor()
        assert isinstance(pm, PerformanceMonitor)

    def test_singleton_behavior(self):
        p1 = get_performance_monitor()
        p2 = get_performance_monitor()
        assert p1 is p2
