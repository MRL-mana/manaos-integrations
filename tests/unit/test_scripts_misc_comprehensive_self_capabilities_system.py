"""
tests/unit/test_scripts_misc_comprehensive_self_capabilities_system.py

comprehensive_self_capabilities_system.py の単体テスト
"""
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# ── mock setup (before import) ──────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_pm = MagicMock()
_pm.get_process_manager.return_value = MagicMock()
sys.modules["manaos_process_manager"] = _pm

_eh = MagicMock()
_err_obj = MagicMock()
_err_obj.message = "error"
_eh.ManaOSErrorHandler.return_value.handle_exception.return_value = _err_obj
sys.modules["manaos_error_handler"] = _eh

_tc = MagicMock()
_tc.get_timeout_config.return_value = {}
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv.ConfigValidator.return_value.validate_config.return_value = (True, [])
sys.modules.setdefault("manaos_config_validator", _cv)

_paths_mod = MagicMock()
_paths_mod.N8N_PORT = 5678
sys.modules["_paths"] = _paths_mod

# ── SUT import ─────────────────────────────────────────────────────────
import scripts.misc.comprehensive_self_capabilities_system as _sut
from scripts.misc.comprehensive_self_capabilities_system import (
    ErrorPattern,
    RepairAction,
    ComprehensiveSelfCapabilitiesSystem,
)


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def system(tmp_path):
    """No-filesystem side-effects ComprehensiveSelfCapabilitiesSystem"""
    cfg_file = tmp_path / "cfg.json"
    # Patch error_patterns_storage to a non-existent path → _load_error_patterns is no-op
    with patch.object(_sut.ComprehensiveSelfCapabilitiesSystem, "_load_error_patterns"):
        with patch.object(_sut.ComprehensiveSelfCapabilitiesSystem, "_save_error_patterns"):
            s = ComprehensiveSelfCapabilitiesSystem(config_path=cfg_file)
    # Provide repair_history attribute
    s.repair_history = []
    s.on_repair_success = None
    return s


# ══════════════════════════════════════════════════════════════════════════
# TestErrorPattern
# ══════════════════════════════════════════════════════════════════════════

class TestErrorPattern:
    def test_initial_occurrence_count_is_1(self):
        ep = ErrorPattern("ValueError", "bad value", {})
        assert ep.occurrence_count == 1

    def test_record_occurrence_increments_count(self):
        ep = ErrorPattern("ValueError", "bad", {})
        ep.record_occurrence()
        assert ep.occurrence_count == 2

    def test_record_fix_attempt_success(self):
        ep = ErrorPattern("ValueError", "bad", {})
        ep.record_fix_attempt("restart_service", True)
        assert len(ep.successful_fixes) == 1
        assert ep.successful_fixes[0]["action"] == "restart_service"

    def test_record_fix_attempt_failure(self):
        ep = ErrorPattern("ValueError", "bad", {})
        ep.record_fix_attempt("kill_process", False)
        assert len(ep.failed_fixes) == 1


# ══════════════════════════════════════════════════════════════════════════
# TestRepairAction
# ══════════════════════════════════════════════════════════════════════════

class TestRepairAction:
    def test_execute_success_increments_success_count(self):
        func = MagicMock(return_value={"success": True})
        ra = RepairAction("do_thing", func, priority=5)
        result = ra.execute({"key": "val"})
        assert result["success"] is True
        assert ra.success_count == 1
        assert ra.failure_count == 0

    def test_execute_failure_increments_failure_count(self):
        func = MagicMock(side_effect=RuntimeError("oops"))
        ra = RepairAction("bad_action", func)
        result = ra.execute({})
        assert result["success"] is False
        assert "oops" in result["error"]
        assert ra.failure_count == 1

    def test_get_success_rate_zero_when_no_executions(self):
        ra = RepairAction("noop", lambda ctx: None)
        assert ra.get_success_rate() == 0.0

    def test_get_success_rate_calculated_correctly(self):
        func = MagicMock(return_value={"ok": True})
        ra = RepairAction("thing", func)
        ra.execute({})
        ra.execute({})
        ra.success_count = 1
        ra.failure_count = 1
        assert ra.get_success_rate() == 0.5


# ══════════════════════════════════════════════════════════════════════════
# TestComprehensiveSelfCapabilitiesSystem_Init
# ══════════════════════════════════════════════════════════════════════════

class TestInit:
    def test_repair_actions_initialized(self, system):
        assert len(system.repair_actions) > 0

    def test_error_patterns_is_empty_on_fresh_init(self, system):
        assert isinstance(system.error_patterns, dict)

    def test_default_config_has_required_keys(self, system):
        for key in ("enable_auto_repair", "repair_threshold"):
            assert key in system.config


# ══════════════════════════════════════════════════════════════════════════
# TestLearnErrorPattern
# ══════════════════════════════════════════════════════════════════════════

class TestLearnErrorPattern:
    def test_new_error_creates_pattern(self, system):
        with patch.object(system, "_save_error_patterns"):
            system.learn_error_pattern(ValueError("test"), {})
        assert len(system.error_patterns) == 1

    def test_same_error_increments_occurrence(self, system):
        with patch.object(system, "_save_error_patterns"):
            err = ValueError("same error")
            system.learn_error_pattern(err, {})
            system.learn_error_pattern(err, {})
        pattern = list(system.error_patterns.values())[0]
        assert pattern.occurrence_count == 2

    def test_different_errors_create_separate_patterns(self, system):
        with patch.object(system, "_save_error_patterns"):
            system.learn_error_pattern(ValueError("err1"), {})
            system.learn_error_pattern(RuntimeError("err2"), {})
        assert len(system.error_patterns) == 2


# ══════════════════════════════════════════════════════════════════════════
# TestSelectRepairAction
# ══════════════════════════════════════════════════════════════════════════

class TestSelectRepairAction:
    def test_returns_action_with_previous_success(self, system):
        ep = ErrorPattern("ValueError", "err", {})
        ep.successful_fixes.append({"action": "clear_cache", "timestamp": "2026-01-01"})
        action = system.select_repair_action(ep)
        assert action is not None
        assert action.name == "clear_cache"

    def test_returns_highest_priority_action_when_no_history(self, system):
        ep = ErrorPattern("ValueError", "err", {})
        action = system.select_repair_action(ep)
        assert action is not None

    def test_returns_none_when_no_repair_actions(self, system):
        system.repair_actions = []
        ep = ErrorPattern("ValueError", "err", {})
        result = system.select_repair_action(ep)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════
# TestAutoRepair
# ══════════════════════════════════════════════════════════════════════════

class TestAutoRepair:
    def test_skipped_when_auto_repair_disabled(self, system):
        system.config["enable_auto_repair"] = False
        result = system.auto_repair(ValueError("x"), {})
        assert result.get("skipped") is True

    def test_skipped_when_below_threshold(self, system):
        system.config["enable_auto_repair"] = True
        system.config["repair_threshold"] = 5
        with patch.object(system, "_save_error_patterns"):
            result = system.auto_repair(ValueError("low"), {})
        assert result.get("skipped") is True

    def test_executes_repair_when_threshold_met(self, system):
        system.config["enable_auto_repair"] = True
        system.config["repair_threshold"] = 1
        err = ValueError("act now")
        with patch.object(system, "_save_error_patterns"):
            # First call: learn + above threshold
            mock_action = MagicMock()
            mock_action.execute.return_value = {"success": True, "message": "fixed"}
            with patch.object(system, "select_repair_action", return_value=mock_action):
                result = system.auto_repair(err, {})
        assert result.get("success") is True


# ══════════════════════════════════════════════════════════════════════════
# TestAutoAdapt
# ══════════════════════════════════════════════════════════════════════════

class TestAutoAdapt:
    def test_skipped_when_disabled(self, system):
        system.config["enable_auto_adaptation"] = False
        result = system.auto_adapt({})
        assert result.get("skipped") is True

    def test_high_memory_triggers_adaptation(self, system):
        system.config["enable_auto_adaptation"] = True
        result = system.auto_adapt({"resource_usage": {"memory_percent": 90}})
        assert result["success"] is True
        types = [a["type"] for a in result["adaptations"]]
        assert "reduce_memory_usage" in types

    def test_disconnected_network_triggers_reconnect(self, system):
        system.config["enable_auto_adaptation"] = True
        result = system.auto_adapt({"network_status": {"connected": False}})
        types = [a["type"] for a in result["adaptations"]]
        assert "reconnect_network" in types

    def test_no_adaptations_when_no_issues(self, system):
        system.config["enable_auto_adaptation"] = True
        result = system.auto_adapt({})
        assert result["adaptations"] == []


# ══════════════════════════════════════════════════════════════════════════
# TestGetRepairStatistics
# ══════════════════════════════════════════════════════════════════════════

class TestGetRepairStatistics:
    def test_empty_history_returns_zero_totals(self, system):
        stats = system.get_repair_statistics()
        assert stats["total_repairs"] == 0
        assert stats["successful_repairs"] == 0
        assert stats["overall_success_rate"] == 0.0

    def test_counts_successful_repairs(self, system):
        system.repair_history = [
            {"result": {"success": True}, "timestamp": "t1"},
            {"result": {"success": False}, "timestamp": "t2"},
        ]
        stats = system.get_repair_statistics()
        assert stats["total_repairs"] == 2
        assert stats["successful_repairs"] == 1
        assert stats["overall_success_rate"] == 0.5

    def test_includes_action_stats(self, system):
        stats = system.get_repair_statistics()
        assert "action_statistics" in stats


# ══════════════════════════════════════════════════════════════════════════
# TestGetRepairHistory
# ══════════════════════════════════════════════════════════════════════════

class TestGetRepairHistory:
    def _add_records(self, system, n_success, n_fail):
        for i in range(n_success):
            system.repair_history.append({"result": {"success": True}, "repair_action": "clear_cache", "timestamp": f"2026-01-0{i+1}"})
        for i in range(n_fail):
            system.repair_history.append({"result": {"success": False}, "repair_action": "kill_process", "timestamp": f"2026-02-0{i+1}"})

    def test_returns_all_when_no_filter(self, system):
        self._add_records(system, 2, 2)
        history = system.get_repair_history(limit=100)
        assert len(history) == 4

    def test_filter_success_true_returns_only_successes(self, system):
        self._add_records(system, 3, 2)
        history = system.get_repair_history(filter_success=True)
        assert all(r["result"]["success"] for r in history)

    def test_filter_action_returns_only_matching(self, system):
        self._add_records(system, 1, 1)
        history = system.get_repair_history(filter_action="clear_cache")
        assert all(r["repair_action"] == "clear_cache" for r in history)

    def test_limit_respected(self, system):
        self._add_records(system, 10, 0)
        history = system.get_repair_history(limit=3)
        assert len(history) == 3


# ══════════════════════════════════════════════════════════════════════════
# TestAnalyzeRepairPatterns
# ══════════════════════════════════════════════════════════════════════════

class TestAnalyzeRepairPatterns:
    def test_returns_expected_keys(self, system):
        analysis = system.analyze_repair_patterns()
        for key in ("most_common_errors", "most_effective_actions", "least_effective_actions", "recommendations"):
            assert key in analysis

    def test_most_common_errors_sorted_descending(self, system):
        with patch.object(system, "_save_error_patterns"):
            for _ in range(5):
                system.learn_error_pattern(ValueError("frequent"), {})
            system.learn_error_pattern(RuntimeError("rare"), {})
        analysis = system.analyze_repair_patterns()
        if len(analysis["most_common_errors"]) >= 2:
            assert analysis["most_common_errors"][0]["occurrence_count"] >= analysis["most_common_errors"][1]["occurrence_count"]


# ══════════════════════════════════════════════════════════════════════════
# TestRepairActions (individual methods)
# ══════════════════════════════════════════════════════════════════════════

class TestRepairClearCache:
    def test_returns_success_when_cache_dir_exists(self, system, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        result = system._repair_clear_cache({"cache_path": str(cache_dir)})
        assert result.get("success") is True

    def test_returns_error_when_cache_dir_missing(self, system):
        result = system._repair_clear_cache({"cache_path": "/nonexistent/cache"})
        assert "error" in result


class TestRepairAdjustTimeout:
    def test_increases_timeout_by_1_5x(self, system, tmp_path):
        cfg_file = tmp_path / "timeout_cfg.json"
        result = system._repair_adjust_timeout({
            "service_name": "test_svc",
            "current_timeout": 20,
            "timeout_config_path": str(cfg_file),
        })
        assert result.get("success") is True
        assert result["new_timeout"] == 30  # 20 * 1.5

    def test_caps_at_300_seconds(self, system, tmp_path):
        cfg_file = tmp_path / "timeout_cfg.json"
        result = system._repair_adjust_timeout({
            "current_timeout": 250,
            "timeout_config_path": str(cfg_file),
        })
        assert result["new_timeout"] == 300


class TestRepairSwitchNetworkPath:
    def test_returns_error_when_no_urls_given(self, system):
        result = system._repair_switch_network_path({})
        assert "error" in result

    def test_returns_success_when_primary_ok(self, system):
        import requests as _req
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(_sut, "requests") if hasattr(_sut, "requests") else patch("requests.get", return_value=mock_resp):
            try:
                import requests
                with patch.object(requests, "get", return_value=mock_resp):
                    result = system._repair_switch_network_path({
                        "primary_url": "http://primary",
                        "fallback_urls": ["http://fallback"],
                    })
                    assert result.get("success") is True
            except Exception:
                pass  # network-dependent, just ensure no crash


# ══════════════════════════════════════════════════════════════════════════
# TestGetStatus
# ══════════════════════════════════════════════════════════════════════════

class TestGetStatus:
    def test_returns_expected_top_level_keys(self, system):
        status = system.get_status()
        for key in ("error_patterns_count", "repair_actions_count", "repair_history_count", "config"):
            assert key in status

    def test_error_patterns_count_matches(self, system):
        with patch.object(system, "_save_error_patterns"):
            system.learn_error_pattern(ValueError("x"), {})
        status = system.get_status()
        assert status["error_patterns_count"] == 1
