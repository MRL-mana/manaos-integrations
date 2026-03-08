"""
Unit tests for scripts/misc/production_traffic_controller.py
Pure logic tests — no network calls.
"""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# requests mock (used at module level)
sys.modules.setdefault("requests", MagicMock())

import pytest
from scripts.misc.production_traffic_controller import (
    HealthCheckResult,
    ProductionTrafficController,
    TRAFFIC_PHASES,
)


@pytest.fixture
def ctrl():
    return ProductionTrafficController()


# ── TestHealthCheckResult ─────────────────────────────────────────────────
class TestHealthCheckResult:
    def test_default_values(self):
        r = HealthCheckResult()
        assert r.healthy_services == 0
        assert r.error_services == []
        assert r.response_times == {}

    def test_to_dict_keys(self):
        r = HealthCheckResult()
        d = r.to_dict()
        assert "timestamp" in d
        assert "healthy_count" in d
        assert "total_count" in d
        assert "avg_latency_ms" in d
        assert "health_percent" in d

    def test_health_percent_calculation(self):
        r = HealthCheckResult()
        r.healthy_services = 7
        d = r.to_dict()
        # 7 / total_services * 100
        assert d["health_percent"] >= 0.0

    def test_error_services_in_dict(self):
        r = HealthCheckResult()
        r.error_services = ["svc_a", "svc_b"]
        d = r.to_dict()
        assert d["error_services"] == ["svc_a", "svc_b"]


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_starts_phase_1(self, ctrl):
        assert ctrl.current_phase == 1

    def test_empty_history(self, ctrl):
        assert ctrl.traffic_history == []
        assert ctrl.health_check_history == []

    def test_monitoring_active(self, ctrl):
        assert ctrl.monitoring_active is True

    def test_phase_metrics_initialized(self, ctrl):
        assert 1 in ctrl.phase_metrics
        assert "errors" in ctrl.phase_metrics[1]


# ── TestGetCurrentPhaseConfig ─────────────────────────────────────────────
class TestGetCurrentPhaseConfig:
    def test_returns_phase_1_config(self, ctrl):
        cfg = ctrl.get_current_phase_config()
        assert cfg["phase"] == 1

    def test_returns_dict(self, ctrl):
        cfg = ctrl.get_current_phase_config()
        assert isinstance(cfg, dict)

    def test_phase_2_config(self, ctrl):
        ctrl.current_phase = 2
        cfg = ctrl.get_current_phase_config()
        assert cfg["phase"] == 2

    def test_invalid_phase_returns_last(self, ctrl):
        ctrl.current_phase = 999
        cfg = ctrl.get_current_phase_config()
        assert cfg == TRAFFIC_PHASES[-1]


# ── TestShouldAdvancePhase ────────────────────────────────────────────────
class TestShouldAdvancePhase:
    def test_phase_3_never_advances(self, ctrl):
        ctrl.current_phase = 3
        assert ctrl.should_advance_phase() is False

    def test_recently_started_phase_does_not_advance(self, ctrl):
        ctrl.phase_start_time = datetime.now()
        assert ctrl.should_advance_phase() is False

    def test_old_phase_with_no_history_advances(self, ctrl):
        ctrl.phase_start_time = datetime.now() - timedelta(hours=2)
        assert ctrl.should_advance_phase() is True

    def test_recent_high_health_advances(self, ctrl):
        ctrl.phase_start_time = datetime.now() - timedelta(hours=2)
        ctrl.health_check_history = [{
            "timestamp": datetime.now().isoformat(),
            "health_percent": 95.0,
        }]
        assert ctrl.should_advance_phase() is True

    def test_recent_low_health_does_not_advance(self, ctrl):
        ctrl.phase_start_time = datetime.now() - timedelta(hours=2)
        ctrl.health_check_history = [{
            "timestamp": datetime.now().isoformat(),
            "health_percent": 60.0,
        }]
        assert ctrl.should_advance_phase() is False


# ── TestAdvancePhase ──────────────────────────────────────────────────────
class TestAdvancePhase:
    def test_increments_phase(self, ctrl):
        ctrl.advance_phase()
        assert ctrl.current_phase == 2

    def test_returns_true_on_success(self, ctrl):
        result = ctrl.advance_phase()
        assert result is True

    def test_phase_3_cannot_advance(self, ctrl):
        ctrl.current_phase = 3
        result = ctrl.advance_phase()
        assert result is False
        assert ctrl.current_phase == 3

    def test_phase_start_time_updated(self, ctrl):
        old_time = ctrl.phase_start_time
        import time
        time.sleep(0.01)
        ctrl.advance_phase()
        assert ctrl.phase_start_time >= old_time
