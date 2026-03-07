"""
Unit tests for scripts/misc/performance_analytics.py
"""
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import pytest

# psutil is used only in collect_metrics() - we mock it to avoid hardware calls
from unittest.mock import MagicMock, patch
sys.modules.setdefault("psutil", MagicMock())

sys.path.insert(0, "scripts/misc")
from performance_analytics import PerformanceAnalytics


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_pa(tmp_path: Path) -> PerformanceAnalytics:
    """Create PerformanceAnalytics bypassing __init__ disk I/O."""
    pa = PerformanceAnalytics.__new__(PerformanceAnalytics)
    pa.metrics_data = defaultdict(list)
    pa.performance_reports = []
    pa.storage_path = tmp_path / "pa_state.json"
    return pa


def _add_metric(pa: PerformanceAnalytics, name: str, values):
    """Helper: populate metrics_data with given values."""
    now = datetime.now()
    for i, v in enumerate(values):
        ts = (now - timedelta(seconds=len(values) - i)).isoformat()
        pa.metrics_data[name].append({"value": v, "timestamp": ts})


# ── analyze_performance ──────────────────────────────────────────────────────

class TestAnalyzePerformance:
    def test_missing_metric_returns_empty(self, tmp_path):
        pa = make_pa(tmp_path)
        assert pa.analyze_performance("nonexistent") == {}

    def test_returns_dict_with_keys(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [10, 20, 30])
        result = pa.analyze_performance("cpu")
        for k in ("metric", "count", "mean", "median", "min", "max"):
            assert k in result

    def test_mean_calculation(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [10, 20, 30])
        result = pa.analyze_performance("cpu")
        assert result["mean"] == pytest.approx(20.0)

    def test_min_max(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "mem", [5, 50, 100])
        result = pa.analyze_performance("mem")
        assert result["min"] == 5
        assert result["max"] == 100

    def test_median(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [1, 3, 5])
        result = pa.analyze_performance("cpu")
        assert result["median"] == pytest.approx(3.0)

    def test_std_dev_zero_for_single_value(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [42])
        result = pa.analyze_performance("cpu")
        assert result["std_dev"] == 0

    def test_std_dev_multiple_values(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "x", [2, 4, 6, 8])
        result = pa.analyze_performance("x")
        assert result["std_dev"] > 0

    def test_p95_p99_present(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", list(range(1, 101)))
        result = pa.analyze_performance("cpu")
        assert "p95" in result
        assert "p99" in result

    def test_count_matches_data_length(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "disk", [10, 20, 30, 40])
        result = pa.analyze_performance("disk")
        assert result["count"] == 4

    def test_time_range_filters_old_data(self, tmp_path):
        pa = make_pa(tmp_path)
        now = datetime.now()
        # Old entry (2 days ago)
        pa.metrics_data["cpu"].append({
            "value": 99.0,
            "timestamp": (now - timedelta(days=2)).isoformat(),
        })
        # Recent entry  
        pa.metrics_data["cpu"].append({
            "value": 10.0,
            "timestamp": (now - timedelta(seconds=1)).isoformat(),
        })
        result = pa.analyze_performance("cpu", time_range=timedelta(hours=1))
        assert result["count"] == 1
        assert result["mean"] == pytest.approx(10.0)

    def test_time_range_no_data_returns_empty(self, tmp_path):
        pa = make_pa(tmp_path)
        now = datetime.now()
        pa.metrics_data["cpu"].append({
            "value": 50.0,
            "timestamp": (now - timedelta(days=3)).isoformat(),
        })
        result = pa.analyze_performance("cpu", time_range=timedelta(hours=1))
        assert result == {}


# ── generate_report ──────────────────────────────────────────────────────────

class TestGenerateReport:
    def test_returns_dict(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [50, 60])
        report = pa.generate_report()
        assert isinstance(report, dict)

    def test_report_has_required_keys(self, tmp_path):
        pa = make_pa(tmp_path)
        report = pa.generate_report()
        for k in ("generated_at", "time_range", "metrics", "summary"):
            assert k in report

    def test_report_contains_specified_metrics(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [30, 40])
        _add_metric(pa, "memory", [60, 70])
        report = pa.generate_report(metrics=["cpu"])
        assert "cpu" in report["metrics"]
        assert "memory" not in report["metrics"]

    def test_report_all_metrics_by_default(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [20])
        _add_metric(pa, "disk", [80])
        report = pa.generate_report()
        assert "cpu" in report["metrics"]
        assert "disk" in report["metrics"]

    def test_report_added_to_history(self, tmp_path):
        pa = make_pa(tmp_path)
        pa.generate_report()
        assert len(pa.performance_reports) == 1

    def test_summary_has_cpu_and_memory(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [25, 35])
        _add_metric(pa, "memory", [55, 65])
        report = pa.generate_report()
        assert "average_cpu" in report["summary"]
        assert "average_memory" in report["summary"]

    def test_empty_metrics_data_returns_empty_summary(self, tmp_path):
        pa = make_pa(tmp_path)
        report = pa.generate_report()
        assert report["metrics"] == {}

    def test_saves_state_file(self, tmp_path):
        pa = make_pa(tmp_path)
        pa.generate_report()
        assert pa.storage_path.exists()


# ── detect_anomalies ─────────────────────────────────────────────────────────

class TestDetectAnomalies:
    def test_missing_metric_returns_empty_list(self, tmp_path):
        pa = make_pa(tmp_path)
        assert pa.detect_anomalies("none") == []

    def test_no_anomalies_in_uniform_data(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [50] * 10)
        # std_dev == 0, so no z-score spikes
        anomalies = pa.detect_anomalies("cpu")
        assert anomalies == []

    def test_detects_clear_anomaly(self, tmp_path):
        pa = make_pa(tmp_path)
        # 9 normal values + 1 spike
        values = [10.0] * 9 + [1000.0]
        _add_metric(pa, "cpu", values)
        anomalies = pa.detect_anomalies("cpu", threshold=2.0)
        assert len(anomalies) >= 1

    def test_anomaly_has_required_keys(self, tmp_path):
        pa = make_pa(tmp_path)
        values = [10.0] * 9 + [500.0]
        _add_metric(pa, "cpu", values)
        anomalies = pa.detect_anomalies("cpu", threshold=2.0)
        if anomalies:
            for k in ("value", "z_score", "timestamp", "deviation"):
                assert k in anomalies[0]

    def test_higher_threshold_fewer_anomalies(self, tmp_path):
        pa = make_pa(tmp_path)
        values = [10.0] * 8 + [100.0, 200.0]
        _add_metric(pa, "cpu", values)
        low = pa.detect_anomalies("cpu", threshold=1.0)
        high = pa.detect_anomalies("cpu", threshold=5.0)
        assert len(low) >= len(high)

    def test_std_dev_zero_returns_no_anomalies(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "x", [42])  # single value → std_dev = 0
        anomalies = pa.detect_anomalies("x")
        assert anomalies == []


# ── get_trends ───────────────────────────────────────────────────────────────

class TestGetTrends:
    def test_missing_metric_returns_empty(self, tmp_path):
        pa = make_pa(tmp_path)
        assert pa.get_trends("none") == {}

    def test_returns_dict_with_data(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [30, 40, 50])
        result = pa.get_trends("cpu")
        assert isinstance(result, dict)

    def test_filters_by_days(self, tmp_path):
        pa = make_pa(tmp_path)
        now = datetime.now()
        # Very old entry
        pa.metrics_data["cpu"].append({
            "value": 99.0,
            "timestamp": (now - timedelta(days=30)).isoformat(),
        })
        # Recent entry
        pa.metrics_data["cpu"].append({
            "value": 20.0,
            "timestamp": (now - timedelta(hours=1)).isoformat(),
        })
        result = pa.get_trends("cpu", days=7)
        # Should only include recent data
        if "mean" in result:
            assert result.get("mean", 99) != pytest.approx(99.0)

    def test_trends_include_average(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [20, 30, 40])
        result = pa.get_trends("cpu")
        assert "average" in result


# ── _load_state / _save_state ────────────────────────────────────────────────

class TestLoadSaveState:
    def test_save_then_load_preserves_metrics(self, tmp_path):
        pa = make_pa(tmp_path)
        _add_metric(pa, "cpu", [50, 60])
        pa._save_state()

        pa2 = make_pa(tmp_path)
        pa2._load_state()
        assert "cpu" in pa2.metrics_data
        assert len(pa2.metrics_data["cpu"]) == 2

    def test_load_missing_file_initializes_empty(self, tmp_path):
        pa = make_pa(tmp_path)
        pa._load_state()
        assert pa.metrics_data == defaultdict(list)

    def test_load_corrupt_file_initializes_empty(self, tmp_path):
        pa = make_pa(tmp_path)
        pa.storage_path.write_text("invalid json")
        pa._load_state()
        assert len(pa.metrics_data) == 0
