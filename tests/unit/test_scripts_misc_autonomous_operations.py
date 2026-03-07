"""
Unit tests for scripts/misc/autonomous_operations.py
"""
import sys
from unittest.mock import MagicMock, patch

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# _paths is try/except in this module, so setdefault is enough
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.GALLERY_PORT = 5559
_paths_mod.LLM_ROUTING_PORT = 5117
sys.modules["_paths"] = _paths_mod

import pytest
from scripts.misc.autonomous_operations import AutonomousOperations


# ── helpers ────────────────────────────────────────────────────────────────
SERVICE_DEF = {"name": "TestSvc", "port": 9999, "path": "/health", "timeout": 2}


def make_ops(**kwargs) -> AutonomousOperations:
    return AutonomousOperations(**kwargs)


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_default_not_running(self):
        ops = make_ops()
        assert ops.running is False

    def test_check_interval_stored(self):
        ops = make_ops(check_interval=30)
        assert ops.check_interval == 30

    def test_auto_recovery_stored(self):
        ops = make_ops(enable_auto_recovery=True)
        assert ops.enable_auto_recovery is True

    def test_services_list_populated(self):
        ops = make_ops()
        assert len(ops.services) > 0

    def test_stats_initial_total_checks_zero(self):
        ops = make_ops()
        assert ops.stats["total_checks"] == 0

    def test_stats_initial_failures_zero(self):
        ops = make_ops()
        assert ops.stats["health_failures"] == 0


# ── TestCheckServiceHealth ─────────────────────────────────────────────────
class TestCheckServiceHealth:
    def test_returns_true_on_200(self):
        ops = make_ops()
        resp = MagicMock()
        resp.status_code = 200
        with patch("requests.get", return_value=resp):
            result = ops.check_service_health(SERVICE_DEF)
        assert result is True

    def test_returns_false_on_non_200(self):
        ops = make_ops()
        resp = MagicMock()
        resp.status_code = 503
        with patch("requests.get", return_value=resp):
            result = ops.check_service_health(SERVICE_DEF)
        assert result is False

    def test_returns_false_on_exception(self):
        ops = make_ops()
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.ConnectionError("refused")):
            result = ops.check_service_health(SERVICE_DEF)
        assert result is False


# ── TestRunHealthChecks ────────────────────────────────────────────────────
class TestRunHealthChecks:
    def test_returns_dict_with_service_names(self):
        ops = make_ops()
        with patch.object(ops, "check_service_health", return_value=True):
            results = ops.run_health_checks()
        assert isinstance(results, dict)
        assert len(results) == len(ops.services)

    def test_increments_total_checks(self):
        ops = make_ops()
        with patch.object(ops, "check_service_health", return_value=True):
            ops.run_health_checks()
        assert ops.stats["total_checks"] == 1

    def test_increments_failure_count(self):
        ops = make_ops()
        with patch.object(ops, "check_service_health", return_value=False):
            ops.run_health_checks()
        assert ops.stats["health_failures"] == len(ops.services)

    def test_sets_last_check_time(self):
        ops = make_ops()
        with patch.object(ops, "check_service_health", return_value=True):
            ops.run_health_checks()
        assert ops.stats["last_check_time"] is not None

    def test_all_healthy_results(self):
        ops = make_ops()
        with patch.object(ops, "check_service_health", return_value=True):
            results = ops.run_health_checks()
        assert all(v is True for v in results.values())


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_has_uptime_seconds(self):
        ops = make_ops()
        stats = ops.get_stats()
        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] >= 0.0

    def test_includes_total_checks(self):
        ops = make_ops()
        stats = ops.get_stats()
        assert "total_checks" in stats

    def test_uptime_positive_after_init(self):
        ops = make_ops()
        stats = ops.get_stats()
        assert stats["uptime_seconds"] >= 0.0


# ── TestAnalyzeAndReport ───────────────────────────────────────────────────
class TestAnalyzeAndReport:
    def test_no_error_on_all_healthy(self):
        ops = make_ops()
        # Should not raise
        ops.analyze_and_report({"svc1": True, "svc2": True})

    def test_no_error_on_unhealthy(self):
        ops = make_ops()
        ops.analyze_and_report({"svc1": False, "svc2": True})
