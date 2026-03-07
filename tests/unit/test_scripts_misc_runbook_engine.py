"""
tests/unit/test_scripts_misc_runbook_engine.py

scripts/misc/runbook_engine.py の純粋ロジック単体テスト
- _cron_next_run_ok_fallback() — cron 簡易判定
- is_runbook_due()             — スケジュール/日次上限判定
- get_runbooks_due()           — level_int < 4 → []
- execute_runbook_step()       — condition アクション分岐
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

import runbook_engine as re_mod
from runbook_engine import (
    _cron_next_run_ok_fallback,
    is_runbook_due,
    get_runbooks_due,
    execute_runbook_step,
)


# ===========================
# _cron_next_run_ok_fallback
# ===========================

class TestCronNextRunOkFallback:
    def test_none_last_run_returns_true(self):
        assert _cron_next_run_ok_fallback("*/5", None) is True

    def test_empty_last_run_returns_true(self):
        assert _cron_next_run_ok_fallback("*/5", "") is True

    def test_invalid_iso_returns_true(self):
        assert _cron_next_run_ok_fallback("*/5", "not-a-date") is True

    def test_just_ran_not_due_wildcard_5(self):
        # 30 seconds ago < 5 minutes → not due
        last = (datetime.now() - timedelta(seconds=30)).isoformat()
        assert _cron_next_run_ok_fallback("*/5 * * * *", last) is False

    def test_due_after_wildcard_interval(self):
        # 10 minutes ago >= 5 minutes → due
        last = (datetime.now() - timedelta(minutes=10)).isoformat()
        assert _cron_next_run_ok_fallback("*/5 * * * *", last) is True

    def test_widcard_15min_not_due(self):
        last = (datetime.now() - timedelta(minutes=5)).isoformat()
        assert _cron_next_run_ok_fallback("*/15 * * * *", last) is False

    def test_wildcard_15min_due(self):
        last = (datetime.now() - timedelta(minutes=20)).isoformat()
        assert _cron_next_run_ok_fallback("*/15 * * * *", last) is True

    def test_default_60min_not_due(self):
        # 30 min ago < 60 → not due (standard cron "0 * * * *")
        last = (datetime.now() - timedelta(minutes=30)).isoformat()
        assert _cron_next_run_ok_fallback("0 * * * *", last) is False

    def test_default_60min_due(self):
        # 70 min ago >= 60 → due
        last = (datetime.now() - timedelta(minutes=70)).isoformat()
        assert _cron_next_run_ok_fallback("0 * * * *", last) is True

    def test_short_schedule_falls_back_to_60(self):
        # fewer than 5 parts → 60 min default
        last = (datetime.now() - timedelta(minutes=30)).isoformat()
        assert _cron_next_run_ok_fallback("*/5", last) is False  # 30 < 300s=5min
        # short schedule: just "foo" → 60 min default
        assert _cron_next_run_ok_fallback("foo", last) is False

    def test_iso_with_z_suffix_parsed(self):
        last = (datetime.now() - timedelta(minutes=10)).isoformat() + "Z"
        assert _cron_next_run_ok_fallback("*/5 * * * *", last) is True


# ===========================
# is_runbook_due
# ===========================

class TestIsRunbookDue:
    def _rb(self, rid="rb1", schedule="*/5 * * * *", max_daily=24, quiet_skip=False):
        return {
            "id": rid,
            "conditions": {
                "schedule": schedule,
                "max_daily_runs": max_daily,
                "quiet_hours_skip": quiet_skip,
            },
        }

    def test_no_id_returns_false(self):
        assert is_runbook_due({}, {}, {}) is False

    def test_empty_id_returns_false(self):
        assert is_runbook_due({"id": ""}, {}, {}) is False

    def test_max_daily_reached_not_due(self):
        today = date.today().isoformat()
        rb = self._rb(max_daily=3)
        state = {
            "rb1": {
                "runs_today": 3,
                "day_start": today,
                "last_run": (datetime.now() - timedelta(hours=2)).isoformat(),
            }
        }
        assert is_runbook_due(rb, state, {}) is False

    def test_max_daily_not_reached_eligible(self):
        today = date.today().isoformat()
        rb = self._rb(max_daily=10, schedule="*/5 * * * *")
        state = {
            "rb1": {
                "runs_today": 5,
                "day_start": today,
                "last_run": (datetime.now() - timedelta(minutes=10)).isoformat(),
            }
        }
        # 5 < 10 and 10 min >= 5 min → due
        assert is_runbook_due(rb, state, {}) is True

    def test_new_day_resets_runs_today(self):
        # day_start is yesterday → runs_today resets to 0
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        # last_run was 10 min ago → due
        rb = self._rb(max_daily=1, schedule="*/5 * * * *")
        state = {
            "rb1": {
                "runs_today": 99,
                "day_start": yesterday,
                "last_run": (datetime.now() - timedelta(minutes=10)).isoformat(),
            }
        }
        # after reset, runs_today becomes 0 < 1 → check cron → due
        assert is_runbook_due(rb, state, {}) is True

    def test_no_state_for_runbook_uses_defaults(self):
        # empty state → runs_today=0, last_run=None → always due
        rb = self._rb(schedule="0 * * * *")
        assert is_runbook_due(rb, {}, {}) is True

    def test_quiet_skip_false_ignores_quiet_hours(self):
        # quiet_hours_skip=False → quiet hours never checked
        rb = self._rb(quiet_skip=False, schedule="0 * * * *")
        assert is_runbook_due(rb, {}, {}) is True


# ===========================
# get_runbooks_due
# ===========================

class TestGetRunbooksDue:
    def test_level_below_4_returns_empty(self):
        assert get_runbooks_due({}, 3) == []

    def test_level_3_returns_empty(self):
        assert get_runbooks_due({"runbooks_enabled": ["rb1"]}, 3) == []

    def test_level_0_returns_empty(self):
        assert get_runbooks_due({}, 0) == []

    def test_level_1_returns_empty(self):
        assert get_runbooks_due({}, 1) == []

    def test_level_2_returns_empty(self):
        assert get_runbooks_due({}, 2) == []

    def test_level_4_with_no_runbooks_returns_empty(self):
        # no runbooks_enabled → load_runbooks returns []
        assert get_runbooks_due({}, 4) == []

    def test_level_5_with_no_runbooks_returns_empty(self):
        assert get_runbooks_due({}, 5) == []


# ===========================
# execute_runbook_step — condition branch
# ===========================

class TestExecuteRunbookStepCondition:
    """HTTP を呼ばない condition アクションのテスト"""

    def _run(self, step, step_results=None):
        return execute_runbook_step(
            step=step,
            runbook={},
            runbook_id="rb_test",
            orchestrator_url="http://localhost:9999",
            config={},
            step_results=step_results or [],
        )

    # --- any_device_unhealthy ---

    def test_any_device_unhealthy_found_via_health_field(self):
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        sr = [
            {
                "status": "success",
                "result": {"devices": [{"health": "degraded"}]},
            }
        ]
        result, err, extra = self._run(step, sr)
        assert result == "success"
        assert err is None

    def test_any_device_unhealthy_found_via_status_field(self):
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        sr = [
            {
                "status": "success",
                "result": {"devices": [{"status": "unhealthy"}]},
            }
        ]
        result, _, _ = self._run(step, sr)
        assert result == "success"

    def test_any_device_unhealthy_skips_when_all_healthy(self):
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        sr = [
            {
                "status": "success",
                "result": {"devices": [{"health": "healthy"}]},
            }
        ]
        result, msg, _ = self._run(step, sr)
        assert result == "skipped"
        assert "condition not met" in msg

    def test_any_device_unhealthy_skips_on_empty_step_results(self):
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        result, _, _ = self._run(step, [])
        assert result == "skipped"

    def test_any_device_unhealthy_skips_when_step_not_success(self):
        # step_results entry with status != "success" is skipped in loop
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        sr = [
            {
                "status": "failed",
                "result": {"devices": [{"health": "degraded"}]},
            }
        ]
        result, _, _ = self._run(step, sr)
        assert result == "skipped"

    def test_any_device_unhealthy_uses_items_key(self):
        step = {"action": "condition", "condition_type": "any_device_unhealthy"}
        sr = [
            {
                "status": "success",
                "result": {"items": [{"health": "critical"}]},
            }
        ]
        result, _, _ = self._run(step, sr)
        assert result == "success"

    # --- bridge_down ---

    def test_bridge_down_success_when_marked(self):
        step = {"action": "condition", "condition_type": "bridge_down"}
        sr = [{"mark_bridge_down": True}]
        result, err, _ = self._run(step, sr)
        assert result == "success"
        assert err is None

    def test_bridge_down_skipped_when_not_marked(self):
        step = {"action": "condition", "condition_type": "bridge_down"}
        result, msg, _ = self._run(step, [{"mark_bridge_down": False}])
        assert result == "skipped"
        assert "bridge" in msg

    def test_bridge_down_skipped_on_empty(self):
        step = {"action": "condition", "condition_type": "bridge_down"}
        result, _, _ = self._run(step, [])
        assert result == "skipped"

    # --- unknown condition type ---

    def test_unknown_condition_type_returns_success(self):
        step = {"action": "condition", "condition_type": "nonexistent_condition"}
        result, _, _ = self._run(step, [])
        assert result == "success"

    def test_empty_condition_type_returns_success(self):
        step = {"action": "condition", "condition_type": ""}
        result, _, _ = self._run(step, [])
        assert result == "success"

    # --- unknown action ---

    def test_unknown_action_returns_skipped(self):
        step = {"action": "foobar"}
        result, msg, _ = self._run(step, [])
        assert result == "skipped"
        assert "unknown action" in msg

    def test_empty_action_returns_skipped(self):
        # action defaults to "tool" when empty ... actually action="tool" goes to
        # httpx path. But missing action key → default "tool" → httpx called.
        # Test with explicit unknown string:
        step = {"action": "invalid_xyz"}
        result, _, _ = self._run(step, [])
        assert result == "skipped"

    def test_orchestrator_empty_text_returns_skipped(self):
        step = {"action": "orchestrator", "text": ""}
        result, msg, _ = self._run(step, [])
        assert result == "skipped"
        assert "empty" in msg
