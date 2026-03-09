"""
Unit tests for scripts/misc/predictive_maintenance.py
"""
import time
from collections import deque
from unittest.mock import MagicMock, patch

import pytest
from scripts.misc.predictive_maintenance import PredictiveMaintenance, SKLEARN_AVAILABLE


# ── fixture ────────────────────────────────────────────────────────────────
@pytest.fixture
def pm(tmp_path):
    """PredictiveMaintenance with disk I/O redirected to tmp_path."""
    m = PredictiveMaintenance.__new__(PredictiveMaintenance)
    m.history_size = 100
    m.metrics_history = {
        "cpu": deque(maxlen=100),
        "memory": deque(maxlen=100),
        "disk": deque(maxlen=100),
        "network": deque(maxlen=100),
        "timestamp": deque(maxlen=100),
    }
    m.predictions = {}
    m.alerts = []
    m.storage_path = tmp_path / "pm_state.json"
    m.models = {}
    m.scalers = {}
    return m


def _fill_history(pm, n=20, cpu=30.0, mem=40.0, disk=50.0):
    """Fill metrics_history with synthetic data."""
    for i in range(n):
        pm.metrics_history["cpu"].append(cpu + i * 0.1)
        pm.metrics_history["memory"].append(mem + i * 0.1)
        pm.metrics_history["disk"].append(disk + i * 0.05)
        pm.metrics_history["network"].append(5.0)
        pm.metrics_history["timestamp"].append(time.time() + i)


# ── TestCheckThresholds ────────────────────────────────────────────────────
class TestCheckThresholds:
    def test_no_alerts_below_thresholds(self, pm):
        metrics = {"cpu": 50.0, "memory": 60.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        # only threshold-based alerts; no sklearn predictions
        threshold_alerts = [a for a in alerts if a["type"] == "threshold_exceeded"]
        assert threshold_alerts == []

    def test_cpu_high_alert(self, pm):
        metrics = {"cpu": 85.0, "memory": 60.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        types = [a["type"] for a in alerts]
        assert "threshold_exceeded" in types
        exceeded = [a for a in alerts if a["type"] == "threshold_exceeded" and a["metric"] == "cpu"]
        assert len(exceeded) == 1

    def test_memory_high_alert(self, pm):
        metrics = {"cpu": 50.0, "memory": 90.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        exceeded = [
            a for a in alerts
            if a["type"] == "threshold_exceeded" and a["metric"] == "memory"
        ]
        assert len(exceeded) == 1

    def test_disk_high_alert(self, pm):
        metrics = {"cpu": 50.0, "memory": 60.0, "disk": 95.0}
        alerts = pm.check_thresholds(metrics)
        exceeded = [
            a for a in alerts
            if a["type"] == "threshold_exceeded" and a["metric"] == "disk"
        ]
        assert len(exceeded) == 1

    def test_severity_high_when_120pct(self, pm):
        # 80 * 1.2 = 96 → if value > 96, severity=high
        metrics = {"cpu": 97.0, "memory": 60.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        exceeded = [a for a in alerts if a["type"] == "threshold_exceeded" and a["metric"] == "cpu"]
        assert exceeded[0]["severity"] == "high"

    def test_severity_medium_just_above_threshold(self, pm):
        # 80 < value <= 96 → medium
        metrics = {"cpu": 82.0, "memory": 60.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        exceeded = [a for a in alerts if a["type"] == "threshold_exceeded" and a["metric"] == "cpu"]
        assert exceeded[0]["severity"] == "medium"

    def test_alert_appended_to_history(self, pm):
        metrics = {"cpu": 85.0, "memory": 60.0, "disk": 70.0}
        pm.check_thresholds(metrics)
        assert len(pm.alerts) >= 1

    def test_alert_keys(self, pm):
        metrics = {"cpu": 85.0, "memory": 60.0, "disk": 70.0}
        alerts = pm.check_thresholds(metrics)
        a = next(a for a in alerts if a["type"] == "threshold_exceeded")
        for key in ("type", "metric", "value", "threshold", "severity", "timestamp"):
            assert key in a

    def test_saves_state(self, pm):
        pm.check_thresholds({"cpu": 50.0, "memory": 50.0, "disk": 50.0})
        assert pm.storage_path.exists()


# ── TestGetRecommendations ─────────────────────────────────────────────────
class TestGetRecommendations:
    def test_returns_list(self, pm):
        assert isinstance(pm.get_recommendations({}), list)

    def test_no_recs_for_normal_values(self, pm):
        metrics = {"cpu": 50.0, "memory": 60.0, "disk": 70.0}
        recs = pm.get_recommendations(metrics)
        # Should not contain high-usage warnings
        assert not any("高い" in r for r in recs)

    def test_cpu_high_recommendation(self, pm):
        recs = pm.get_recommendations({"cpu": 85.0})
        assert any("CPU" in r for r in recs)

    def test_cpu_low_recommendation(self, pm):
        recs = pm.get_recommendations({"cpu": 10.0})
        assert any("低い" in r or "多くの" in r for r in recs)

    def test_memory_high_recommendation(self, pm):
        recs = pm.get_recommendations({"memory": 90.0})
        assert any("メモリ" in r for r in recs)

    def test_disk_high_recommendation(self, pm):
        recs = pm.get_recommendations({"disk": 95.0})
        assert any("ディスク" in r for r in recs)

    def test_multiple_issues_multiple_recs(self, pm):
        recs = pm.get_recommendations({"cpu": 85.0, "memory": 90.0, "disk": 95.0})
        assert len(recs) >= 3


# ── TestPredictFutureUsage ─────────────────────────────────────────────────
class TestPredictFutureUsage:
    def test_returns_none_for_unknown_metric(self, pm):
        result = pm.predict_future_usage("unknown_metric")
        assert result is None

    def test_returns_none_when_insufficient_history(self, pm):
        # only 3 entries, need >= 10
        for _ in range(3):
            pm.metrics_history["cpu"].append(50.0)
        result = pm.predict_future_usage("cpu")
        assert result is None

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_returns_float_with_enough_history(self, pm, tmp_path):
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import StandardScaler
        pm.models = {
            k: LinearRegression() for k in ["cpu", "memory", "disk"]
        }
        pm.scalers = {
            k: StandardScaler() for k in ["cpu", "memory", "disk"]
        }
        _fill_history(pm, n=20, cpu=30.0)
        result = pm.predict_future_usage("cpu")
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0


# ── TestCollectMetrics ─────────────────────────────────────────────────────
class TestCollectMetrics:
    def test_returns_dict(self, pm):
        with patch("scripts.misc.predictive_maintenance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            mock_psutil.disk_usage.return_value = MagicMock(percent=60.0)
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=1024 * 1024, bytes_recv=2 * 1024 * 1024
            )
            metrics = pm.collect_metrics()
        assert isinstance(metrics, dict)

    def test_contains_expected_keys(self, pm):
        with patch("scripts.misc.predictive_maintenance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            mock_psutil.disk_usage.return_value = MagicMock(percent=60.0)
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=1024 * 1024, bytes_recv=2 * 1024 * 1024
            )
            metrics = pm.collect_metrics()
        for key in ("cpu", "memory", "disk", "timestamp"):
            assert key in metrics

    def test_cpu_value_correct(self, pm):
        with patch("scripts.misc.predictive_maintenance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 45.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            mock_psutil.disk_usage.return_value = MagicMock(percent=60.0)
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=0, bytes_recv=0
            )
            metrics = pm.collect_metrics()
        assert metrics["cpu"] == 45.0

    def test_appends_to_history(self, pm):
        with patch("scripts.misc.predictive_maintenance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            mock_psutil.disk_usage.return_value = MagicMock(percent=60.0)
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=0, bytes_recv=0
            )
            pm.collect_metrics()
        assert len(pm.metrics_history["cpu"]) == 1


# ── TestSaveLoadState ─────────────────────────────────────────────────────
class TestSaveLoadState:
    def test_save_creates_file(self, pm):
        pm._save_state()
        assert pm.storage_path.exists()

    def test_load_when_no_file_leaves_empty(self, pm):
        pm._load_state()
        assert len(pm.metrics_history["cpu"]) == 0

    def test_roundtrip(self, pm):
        pm.metrics_history["cpu"].extend([10.0, 20.0, 30.0])
        pm.alerts = [{"type": "test", "metric": "cpu"}]
        pm._save_state()

        pm2 = PredictiveMaintenance.__new__(PredictiveMaintenance)
        pm2.history_size = 100
        pm2.metrics_history = {
            "cpu": deque(maxlen=100), "memory": deque(maxlen=100),
            "disk": deque(maxlen=100), "network": deque(maxlen=100),
            "timestamp": deque(maxlen=100),
        }
        pm2.alerts = []
        pm2.storage_path = pm.storage_path
        pm2._load_state()
        assert list(pm2.metrics_history["cpu"]) == [10.0, 20.0, 30.0]
        assert len(pm2.alerts) == 1
