# -*- coding: utf-8 -*-
"""tests for scripts/misc/autonomy_system.py"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.misc.autonomy_system import (
    AutonomySystem,
    AutonomyLevel,
    AutonomyTask,
    LEVEL_NAMES,
)


def _make_system(tmp_path: Path, level: int = 4) -> AutonomySystem:
    cfg = {
        "autonomy_level": level,
        "tasks_storage_path": str(tmp_path / "autonomy_tasks.json"),
        "budget_usage_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "autonomy_config.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")
    return AutonomySystem(config_path=cfg_file)


# ---------------------------------------------------------------------------
# AutonomyLevel enum
# ---------------------------------------------------------------------------
class TestAutonomyLevel:
    def test_values(self):
        assert AutonomyLevel.DISABLED.value == "disabled"
        assert AutonomyLevel.LOW.value == "low"
        assert AutonomyLevel.MEDIUM.value == "medium"
        assert AutonomyLevel.HIGH.value == "high"
        assert AutonomyLevel.FULL.value == "full"

    def test_is_str(self):
        assert isinstance(AutonomyLevel.HIGH, str)


# ---------------------------------------------------------------------------
# LEVEL_NAMES
# ---------------------------------------------------------------------------
class TestLevelNames:
    def test_l0(self):
        assert LEVEL_NAMES[0] == "L0_OFF"

    def test_l6(self):
        assert LEVEL_NAMES[6] == "L6_Ops"

    def test_all_present(self):
        for i in range(7):
            assert i in LEVEL_NAMES


# ---------------------------------------------------------------------------
# AutonomyTask dataclass
# ---------------------------------------------------------------------------
class TestAutonomyTask:
    def test_required_fields(self):
        t = AutonomyTask(task_id="t1", task_type="notify", priority="normal", condition={}, action={}, schedule=None)
        assert t.task_id == "t1"
        assert t.task_type == "notify"

    def test_defaults(self):
        t = AutonomyTask(task_id="t2", task_type="x", priority="low", condition={}, action={}, schedule=None)
        assert t.enabled is True
        assert t.last_executed is None
        assert t.execution_count == 0
        assert t.success_count == 0

    def test_created_at_set_automatically(self):
        t = AutonomyTask(task_id="t3", task_type="x", priority="low", condition={}, action={}, schedule=None)
        assert t.created_at != ""
        assert "T" in t.created_at or "-" in t.created_at

    def test_created_at_custom(self):
        t = AutonomyTask(task_id="t4", task_type="x", priority="low",
                         condition={}, action={}, schedule=None, created_at="2025-01-01T00:00:00")
        assert t.created_at == "2025-01-01T00:00:00"


# ---------------------------------------------------------------------------
# AutonomySystem init
# ---------------------------------------------------------------------------
class TestInit:
    def test_default_level(self, tmp_path):
        a = AutonomySystem(config_path=tmp_path / "nonexistent.json")
        assert a.get_level_int() == 4

    def test_config_level_respected(self, tmp_path):
        a = _make_system(tmp_path, level=2)
        assert a.get_level_int() == 2

    def test_level_clamped_max(self, tmp_path):
        a = _make_system(tmp_path, level=99)
        assert a.get_level_int() == 6

    def test_level_clamped_min(self, tmp_path):
        a = _make_system(tmp_path, level=-5)
        assert a.get_level_int() == 0

    def test_config_stored(self, tmp_path):
        a = _make_system(tmp_path)
        assert a.config is not None

    def test_tasks_empty_on_fresh_start(self, tmp_path):
        a = _make_system(tmp_path)
        assert a.tasks == {}

    def test_execution_history_empty(self, tmp_path):
        a = _make_system(tmp_path)
        assert a.execution_history == []


# ---------------------------------------------------------------------------
# set/get_level_int
# ---------------------------------------------------------------------------
class TestSetGetLevel:
    def test_set_level(self, tmp_path):
        a = _make_system(tmp_path, level=4)
        a.set_level_int(2)
        assert a.get_level_int() == 2

    def test_set_level_clamps_above(self, tmp_path):
        a = _make_system(tmp_path)
        a.set_level_int(10)
        assert a.get_level_int() == 6

    def test_set_level_clamps_below(self, tmp_path):
        a = _make_system(tmp_path)
        a.set_level_int(-1)
        assert a.get_level_int() == 0

    def test_set_level_updates_autonomy_level(self, tmp_path):
        a = _make_system(tmp_path)
        a.set_level_int(0)
        # AutonomyLevel enum is also updated
        assert a._level_int == 0


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------
class TestAddTask:
    def _task(self, task_id: str = "t1") -> AutonomyTask:
        return AutonomyTask(task_id=task_id, task_type="notify", priority="normal",
                            condition={}, action={}, schedule=None)

    def test_task_added_to_dict(self, tmp_path):
        a = _make_system(tmp_path)
        t = self._task("task1")
        a.add_task(t)
        assert "task1" in a.tasks

    def test_returns_task(self, tmp_path):
        a = _make_system(tmp_path)
        t = self._task("task2")
        returned = a.add_task(t)
        assert returned.task_id == "task2"

    def test_multiple_tasks(self, tmp_path):
        a = _make_system(tmp_path)
        for i in range(3):
            a.add_task(self._task(f"t{i}"))
        assert len(a.tasks) == 3

    def test_overwrite_same_id(self, tmp_path):
        a = _make_system(tmp_path)
        t1 = self._task("dup")
        t2 = AutonomyTask(task_id="dup", task_type="updated", priority="high",
                          condition={}, action={}, schedule=None)
        a.add_task(t1)
        a.add_task(t2)
        assert a.tasks["dup"].task_type == "updated"
        assert len(a.tasks) == 1


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------
class TestGetStatus:
    def test_required_keys(self, tmp_path):
        a = _make_system(tmp_path)
        s = a.get_status()
        for key in ["autonomy_level_int", "autonomy_level_name", "total_tasks",
                    "enabled_tasks", "total_executions", "timestamp"]:
            assert key in s, f"key={key} missing"

    def test_level_int_matches(self, tmp_path):
        a = _make_system(tmp_path, level=3)
        assert a.get_status()["autonomy_level_int"] == 3

    def test_total_tasks_reflects_added(self, tmp_path):
        a = _make_system(tmp_path)
        t = AutonomyTask(task_id="x", task_type="t", priority="low", condition={}, action={}, schedule=None)
        a.add_task(t)
        assert a.get_status()["total_tasks"] == 1

    def test_timestamp_is_recent(self, tmp_path):
        a = _make_system(tmp_path)
        ts_str = a.get_status()["timestamp"]
        ts = datetime.fromisoformat(ts_str)
        assert (datetime.now() - ts).total_seconds() < 5


# ---------------------------------------------------------------------------
# check_can_execute_tool
# ---------------------------------------------------------------------------
class TestCheckCanExecuteTool:
    def test_level_0_returns_false(self, tmp_path):
        a = _make_system(tmp_path, level=0)
        ok, msg = a.check_can_execute_tool("bash_command")
        assert ok is False
        assert "無効" in msg or "L0" in msg

    def test_level_4_allows_c0_tool(self, tmp_path):
        a = _make_system(tmp_path, level=4)
        ok, msg = a.check_can_execute_tool("cache_stats")  # C0 tool
        assert ok is True

    def test_level_1_allows_c0_tool(self, tmp_path):
        a = _make_system(tmp_path, level=1)
        ok, msg = a.check_can_execute_tool("device_discover")  # C0 tool
        assert ok is True

    def test_returns_tuple(self, tmp_path):
        a = _make_system(tmp_path)
        result = a.check_can_execute_tool("test_tool")
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# record_cost
# ---------------------------------------------------------------------------
class TestRecordCost:
    def test_returns_bool(self, tmp_path):
        a = _make_system(tmp_path)
        result = a.record_cost("llm_calls")
        assert isinstance(result, bool)

    def test_without_autonomy_gates_returns_true(self, tmp_path):
        a = _make_system(tmp_path)
        assert a.record_cost("llm_calls") is True

    def test_custom_period(self, tmp_path):
        a = _make_system(tmp_path)
        assert a.record_cost("image_jobs", period="per_day") is True


# ---------------------------------------------------------------------------
# _check_condition
# ---------------------------------------------------------------------------
class TestCheckCondition:
    def test_always(self, tmp_path):
        a = _make_system(tmp_path)
        assert a._check_condition({"type": "always"}) is True

    def test_empty_condition_always(self, tmp_path):
        a = _make_system(tmp_path)
        assert a._check_condition({}) is True

    def test_time_based_match(self, tmp_path):
        a = _make_system(tmp_path)
        current_hour = datetime.now().hour
        assert a._check_condition({"type": "time_based", "hours": [current_hour]}) is True

    def test_time_based_no_match(self, tmp_path):
        a = _make_system(tmp_path)
        assert a._check_condition({"type": "time_based", "hours": []}) is False

    def test_interval_no_last_executed(self, tmp_path):
        a = _make_system(tmp_path)
        assert a._check_condition({"type": "interval", "interval_seconds": 3600}) is True

    def test_interval_not_elapsed(self, tmp_path):
        a = _make_system(tmp_path)
        recent = (datetime.now() - timedelta(seconds=10)).isoformat()
        result = a._check_condition({
            "type": "interval",
            "interval_seconds": 3600,
            "last_executed": recent
        })
        assert result is False

    def test_interval_elapsed(self, tmp_path):
        a = _make_system(tmp_path)
        old = (datetime.now() - timedelta(hours=2)).isoformat()
        result = a._check_condition({
            "type": "interval",
            "interval_seconds": 3600,
            "last_executed": old
        })
        assert result is True


# ---------------------------------------------------------------------------
# _get_default_config
# ---------------------------------------------------------------------------
class TestDefaultConfig:
    def test_has_autonomy_level(self, tmp_path):
        a = _make_system(tmp_path)
        cfg = a._get_default_config()
        assert "autonomy_level" in cfg

    def test_has_require_confirm_token_classes(self, tmp_path):
        a = _make_system(tmp_path)
        cfg = a._get_default_config()
        assert "require_confirm_token_classes" in cfg

    def test_degrade_policy_present(self, tmp_path):
        a = _make_system(tmp_path)
        cfg = a._get_default_config()
        assert "degrade_policy" in cfg
