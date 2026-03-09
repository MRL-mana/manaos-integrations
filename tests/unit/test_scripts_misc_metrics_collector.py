"""
Unit tests for scripts/misc/metrics_collector.py
"""
import sys
from collections import deque, defaultdict
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# ── external module mocks ──────────────────────────────────────────────────
_ul = MagicMock()
_ul.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("unified_logging", _ul)

import pytest  # noqa: E402, F401
from scripts.misc.metrics_collector import (  # noqa: E402
    Metric,
    MetricsCollector,
)


# ── Helpers ───────────────────────────────────────────────────────────────
def make_collector(tmp_path, max_history=100):
    collector = MetricsCollector.__new__(MetricsCollector)
    collector.max_history = max_history
    collector.metrics = deque(maxlen=max_history)
    collector.counters = defaultdict(int)
    collector.gauges = {}
    collector.histograms = defaultdict(list)
    collector.storage_path = tmp_path / "metrics"
    collector.storage_path.mkdir(parents=True, exist_ok=True)
    return collector


# ── Metric dataclass ──────────────────────────────────────────────────────
class TestMetric:
    def test_create(self):
        m = Metric(name="cpu", value=50.0)
        assert m.name == "cpu"
        assert m.value == 50.0
        assert isinstance(m.timestamp, datetime)
        assert m.tags == {}
        assert m.unit == ""

    def test_custom_tags(self):
        m = Metric(name="req", value=1.0, tags={"env": "prod"})
        assert m.tags["env"] == "prod"

    def test_custom_unit(self):
        m = Metric(name="mem", value=80.0, unit="percent")
        assert m.unit == "percent"


# ── MetricsCollector.record ───────────────────────────────────────────────
class TestRecord:
    def test_appends_metric(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("cpu", 30.0)
        assert len(mc.metrics) == 1

    def test_metric_name_value(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("latency", 0.5, unit="ms")
        m = list(mc.metrics)[0]
        assert m.name == "latency"
        assert m.value == 0.5
        assert m.unit == "ms"

    def test_with_tags(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("req", 1.0, tags={"service": "api"})
        m = list(mc.metrics)[0]
        assert m.tags["service"] == "api"

    def test_max_history_respected(self, tmp_path):
        mc = make_collector(tmp_path, max_history=3)
        for i in range(5):
            mc.record(f"m{i}", float(i))
        assert len(mc.metrics) == 3


# ── MetricsCollector.increment ────────────────────────────────────────────
class TestIncrement:
    def test_increments_counter(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.increment("requests")
        assert mc.counters["requests"] == 1

    def test_increments_twice(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.increment("requests")
        mc.increment("requests")
        assert mc.counters["requests"] == 2

    def test_custom_value(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.increment("bytes", value=1024)
        assert mc.counters["bytes"] == 1024

    def test_also_records_metric(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.increment("requests")
        assert any(m.name == "requests" for m in mc.metrics)

    def test_with_tags_different_key(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.increment("req", tags={"env": "prod"})
        mc.increment("req", tags={"env": "dev"})
        assert mc.counters["req:env=prod"] == 1
        assert mc.counters["req:env=dev"] == 1


# ── MetricsCollector.set_gauge ────────────────────────────────────────────
class TestSetGauge:
    def test_sets_gauge(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.set_gauge("cpu", 75.0)
        assert mc.gauges["cpu"] == 75.0

    def test_overwrites_gauge(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.set_gauge("cpu", 50.0)
        mc.set_gauge("cpu", 80.0)
        assert mc.gauges["cpu"] == 80.0

    def test_also_records_metric(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.set_gauge("mem", 60.0)
        assert any(m.name == "mem" for m in mc.metrics)


# ── MetricsCollector.record_histogram ────────────────────────────────────
class TestRecordHistogram:
    def test_appends_to_histogram(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record_histogram("latency", 0.1)
        mc.record_histogram("latency", 0.2)
        assert len(mc.histograms["latency"]) == 2

    def test_also_records_metric(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record_histogram("resp", 1.5)
        assert any(m.name == "resp" for m in mc.metrics)


# ── MetricsCollector._get_key ─────────────────────────────────────────────
class TestGetKey:
    def test_no_tags(self, tmp_path):
        mc = make_collector(tmp_path)
        assert mc._get_key("cpu", None) == "cpu"

    def test_with_tags_sorted(self, tmp_path):
        mc = make_collector(tmp_path)
        key = mc._get_key("req", {"b": "2", "a": "1"})
        assert key == "req:a=1,b=2"

    def test_empty_tags_dict(self, tmp_path):
        mc = make_collector(tmp_path)
        assert mc._get_key("cpu", {}) == "cpu"


# ── MetricsCollector.get_metrics ─────────────────────────────────────────
class TestGetMetrics:
    def test_returns_all_if_no_filter(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("a", 1.0)
        mc.record("b", 2.0)
        assert len(mc.get_metrics()) == 2

    def test_filter_by_name(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("cpu", 50.0)
        mc.record("mem", 60.0)
        results = mc.get_metrics(name="cpu")
        assert len(results) == 1
        assert results[0].name == "cpu"

    def test_filter_by_tags(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("req", 1.0, tags={"env": "prod"})
        mc.record("req", 2.0, tags={"env": "dev"})
        results = mc.get_metrics(tags={"env": "prod"})
        assert len(results) == 1
        assert results[0].value == 1.0

    def test_filter_by_start_time(self, tmp_path):
        mc = make_collector(tmp_path)
        old_metric = Metric(name="old", value=1.0,
                            timestamp=datetime.now() - timedelta(hours=2))
        mc.metrics.append(old_metric)
        mc.record("new", 2.0)
        results = mc.get_metrics(start_time=datetime.now() - timedelta(hours=1))
        assert all(m.name != "old" for m in results)

    def test_filter_by_end_time(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("new", 1.0)
        future_metric = Metric(name="future", value=2.0,
                               timestamp=datetime.now() + timedelta(hours=2))
        mc.metrics.append(future_metric)
        results = mc.get_metrics(end_time=datetime.now() + timedelta(hours=1))
        assert all(m.name != "future" for m in results)


# ── MetricsCollector.get_statistics ──────────────────────────────────────
class TestGetStatistics:
    def test_empty_returns_empty_dict(self, tmp_path):
        mc = make_collector(tmp_path)
        assert mc.get_statistics("nonexistent") == {}

    def test_statistics_keys(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("cpu", 10.0)
        mc.record("cpu", 20.0)
        stats = mc.get_statistics("cpu")
        assert "count" in stats
        assert "min" in stats
        assert "max" in stats
        assert "avg" in stats
        assert "sum" in stats

    def test_min_max_avg(self, tmp_path):
        mc = make_collector(tmp_path)
        for v in [10.0, 20.0, 30.0]:
            mc.record("cpu", v)
        stats = mc.get_statistics("cpu")
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0
        assert stats["count"] == 3

    def test_filter_by_tags(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("req", 1.0, tags={"env": "prod"})
        mc.record("req", 2.0, tags={"env": "dev"})
        stats = mc.get_statistics("req", tags={"env": "prod"})
        assert stats["count"] == 1


# ── MetricsCollector.collect_system_metrics ───────────────────────────────
class TestCollectSystemMetrics:
    def test_sets_cpu_gauge(self, tmp_path):
        mc = make_collector(tmp_path)
        with patch("scripts.misc.metrics_collector.psutil") as p:
            p.cpu_percent.return_value = 45.0
            p.virtual_memory.return_value = MagicMock(
                percent=60.0, used=4 * 1024**3, available=8 * 1024**3)
            p.disk_usage.return_value = MagicMock(
                percent=30.0, used=100 * 1024**3, free=200 * 1024**3)
            mc.collect_system_metrics()
        assert any("system.cpu.percent" in k for k in mc.gauges)


# ── MetricsCollector.save_metrics / load_metrics ──────────────────────────
class TestSaveLoadMetrics:
    def test_save_creates_file(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("cpu", 50.0)
        save_path = tmp_path / "metrics.json"
        mc.save_metrics(file_path=save_path)
        assert save_path.exists()

    def test_load_metrics(self, tmp_path):
        mc1 = make_collector(tmp_path)
        mc1.record("cpu", 50.0)
        mc1.increment("req")
        save_path = tmp_path / "metrics.json"
        mc1.save_metrics(file_path=save_path)

        mc2 = make_collector(tmp_path)
        mc2.load_metrics(save_path)
        assert len(mc2.metrics) == 2  # cpu + increment


# ── MetricsCollector.get_summary ─────────────────────────────────────────
class TestGetSummary:
    def test_returns_dict(self, tmp_path):
        mc = make_collector(tmp_path)
        summary = mc.get_summary()
        assert isinstance(summary, dict)

    def test_summary_keys(self, tmp_path):
        mc = make_collector(tmp_path)
        summary = mc.get_summary()
        for key in ("total_metrics", "counters", "gauges", "histogram_count",
                    "recent_metrics"):
            assert key in summary

    def test_total_metrics_count(self, tmp_path):
        mc = make_collector(tmp_path)
        mc.record("a", 1.0)
        mc.record("b", 2.0)
        assert mc.get_summary()["total_metrics"] == 2

    def test_recent_metrics_max_10(self, tmp_path):
        mc = make_collector(tmp_path, max_history=1000)
        for i in range(15):
            mc.record(f"m{i}", float(i))
        summary = mc.get_summary()
        assert len(summary["recent_metrics"]) <= 10


# ── get_metrics_collector singleton ──────────────────────────────────────
class TestGetMetricsCollector:
    def test_returns_instance(self):
        import scripts.misc.metrics_collector as mod
        mod._metrics_collector = None  # reset singleton
        with patch.object(MetricsCollector, "__init__", return_value=None):
            mod.get_metrics_collector()  # just check it doesn't raise
        mod._metrics_collector = None  # cleanup
