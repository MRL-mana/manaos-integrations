"""
tests/test_autonomy_system.py
AutonomySystem の単体テスト

対象: scripts/misc/autonomy_system.py
- AutonomyLevel enum
- AutonomyTask dataclass
- AutonomySystem 初期化・レベル管理
- check_can_execute_tool（レベル 0 では拒否）
- _check_condition（always / time_based / interval）
- add_task + タスク永続化
- check_and_execute_tasks / execution_history
"""

import json
import pytest
from datetime import datetime, timedelta
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch


# =====================================================================
# sys.path は conftest.py が設定済み
# =====================================================================
from scripts.misc.autonomy_system import (
    AutonomyLevel,
    AutonomyTask,
    AutonomySystem,
    LEVEL_NAMES,
)


# ----------------------------------------------------------------------
# ヘルパー: テスト用 AutonomySystem（外部依存を排除）
# ----------------------------------------------------------------------

def make_system(tmp_path: Path, level: int = 4) -> AutonomySystem:
    """
    ファイル I/O を tmp_path に誘導した AutonomySystem を返す。
    autonomy_gates / httpx 等の外部呼び出しは patch しない
    （ImportError を raise した場合のフォールバックを使う）。
    """
    config_path = tmp_path / "autonomy_config.json"
    storage_path = tmp_path / "autonomy_tasks.json"

    config = {
        "autonomy_level": level,
        "max_concurrent_tasks": 3,
        "check_interval_seconds": 60,
        "tasks_storage_path": str(storage_path),
        "require_confirm_token_classes": ["C3", "C4"],
        "degrade_policy": {"on_budget_exceeded": 2, "on_repeated_failures": 3},
        "runbooks_enabled": [],
        "runbook_flags": {},
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    return AutonomySystem(
        orchestrator_url="http://127.0.0.1:9999",
        config_path=config_path,
    )


def make_task(task_id: str = "t001", condition_type: str = "always") -> AutonomyTask:
    return AutonomyTask(
        task_id=task_id,
        task_type="test_task",
        priority="low",
        condition={"type": condition_type},
        action={"type": "orchestrator", "intent": "test"},
        schedule=None,
    )


# ======================================================================
# 1. AutonomyLevel enum
# ======================================================================

class TestAutonomyLevel:
    def test_enum_values_exist(self) -> None:
        for name in ("DISABLED", "LOW", "MEDIUM", "HIGH", "FULL"):
            assert hasattr(AutonomyLevel, name)

    def test_disabled_value(self) -> None:
        assert AutonomyLevel.DISABLED.value == "disabled"

    def test_full_value(self) -> None:
        assert AutonomyLevel.FULL.value == "full"

    def test_isinstance_str(self) -> None:
        # StrEnum なので str として使える
        assert isinstance(AutonomyLevel.MEDIUM, str)


# ======================================================================
# 2. LEVEL_NAMES
# ======================================================================

class TestLevelNames:
    def test_zero_is_off(self) -> None:
        assert LEVEL_NAMES[0] == "L0_OFF"

    def test_six_is_ops(self) -> None:
        assert LEVEL_NAMES[6] == "L6_Ops"

    def test_all_levels_present(self) -> None:
        for i in range(7):
            assert i in LEVEL_NAMES


# ======================================================================
# 3. AutonomyTask dataclass
# ======================================================================

class TestAutonomyTask:
    def test_created_at_auto_set(self) -> None:
        task = make_task()
        assert task.created_at != ""

    def test_defaults(self) -> None:
        task = make_task()
        assert task.enabled is True
        assert task.execution_count == 0
        assert task.success_count == 0
        assert task.last_executed is None

    def test_asdict_roundtrip(self) -> None:
        task = make_task("t_roundtrip")
        d = asdict(task)
        reconstructed = AutonomyTask(**d)
        assert reconstructed.task_id == task.task_id


# ======================================================================
# 4. AutonomySystem 初期化
# ======================================================================

class TestAutonomySystemInit:
    def test_default_level_int(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=4)
        assert sys.get_level_int() == 4

    def test_level_enum_high(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=4)
        assert sys.autonomy_level == AutonomyLevel.HIGH

    def test_level_zero_disabled(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=0)
        assert sys.autonomy_level == AutonomyLevel.DISABLED

    def test_level_five_full(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=5)
        assert sys.autonomy_level == AutonomyLevel.FULL

    def test_tasks_empty_on_init(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert isinstance(sys.tasks, dict)

    def test_execution_history_empty(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys.execution_history == []


# ======================================================================
# 5. レベル変更
# ======================================================================

class TestLevelManagement:
    def test_set_level_int(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=4)
        sys.set_level_int(2)
        assert sys.get_level_int() == 2
        assert sys.autonomy_level == AutonomyLevel.LOW

    def test_clamp_min_zero(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        sys.set_level_int(-5)
        assert sys.get_level_int() == 0

    def test_clamp_max_six(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        sys.set_level_int(100)
        assert sys.get_level_int() == 6

    def test_parse_legacy_disabled(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys._parse_legacy_level("disabled") == 0

    def test_parse_legacy_full(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys._parse_legacy_level("full") == 5

    def test_level_to_legacy_three_is_medium(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys._level_to_legacy_enum(3) == AutonomyLevel.MEDIUM


# ======================================================================
# 6. _check_condition
# ======================================================================

class TestCheckCondition:
    def test_always_true(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys._check_condition({"type": "always"}) is True

    def test_unknown_type_false(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        assert sys._check_condition({"type": "undefined_type_xyz"}) is False

    def test_time_based_match(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        current_hour = datetime.now().hour
        assert sys._check_condition({"type": "time_based", "hours": [current_hour]}) is True

    def test_time_based_no_match(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        # 現在時刻 +1 だけの配列 → マッチしない（24時間前提で 23 なら 0 に正規化も必要）
        other_hour = (datetime.now().hour + 13) % 24
        assert sys._check_condition({"type": "time_based", "hours": [other_hour]}) is False

    def test_interval_no_last_executed(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        # last_executed が未設定 → True（初回実行を許可）
        assert sys._check_condition({"type": "interval", "interval_seconds": 3600}) is True

    def test_interval_not_elapsed(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        recent = (datetime.now() - timedelta(seconds=10)).isoformat()
        assert sys._check_condition({
            "type": "interval",
            "interval_seconds": 3600,
            "last_executed": recent
        }) is False

    def test_interval_elapsed(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        old = (datetime.now() - timedelta(hours=2)).isoformat()
        assert sys._check_condition({
            "type": "interval",
            "interval_seconds": 3600,
            "last_executed": old
        }) is True


# ======================================================================
# 7. add_task / タスク永続化
# ======================================================================

class TestAddTask:
    def test_add_task_in_memory(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        task = make_task("t_add")
        sys.add_task(task)
        assert "t_add" in sys.tasks

    def test_add_task_persisted(self, tmp_path: Path) -> None:
        storage = tmp_path / "autonomy_tasks.json"
        sys = make_system(tmp_path)
        sys.add_task(make_task("t_persist"))
        assert storage.exists()
        data = json.loads(storage.read_text(encoding="utf-8"))
        ids = [t["task_id"] for t in data["tasks"]]
        assert "t_persist" in ids

    def test_add_multiple_tasks(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path)
        for i in range(5):
            sys.add_task(make_task(f"t_{i:03d}"))
        assert len(sys.tasks) == 5


# ======================================================================
# 8. check_and_execute_tasks（レベル 0 → 空）
# ======================================================================

class TestCheckAndExecuteTasks:
    def test_level_zero_returns_empty(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=0)
        sys.add_task(make_task("t_noop"))
        results = sys.check_and_execute_tasks()
        assert results == []

    def test_no_tasks_returns_empty(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=4)
        results = sys.check_and_execute_tasks()
        assert isinstance(results, list)


# ======================================================================
# 9. check_can_execute_tool（autonomy_gates が無い環境でのフォールバック）
# ======================================================================

class TestCheckCanExecuteTool:
    def test_level_zero_denied(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=0)
        # autonomy_gates が無い場合は ImportError → L0 なら False
        with patch.dict("sys.modules", {"autonomy_gates": None}):
            allowed, reason = sys.check_can_execute_tool("some_tool")
        assert allowed is False
        assert "L0" in reason or reason != ""

    def test_level_nonzero_allowed_without_gates(self, tmp_path: Path) -> None:
        sys = make_system(tmp_path, level=4)
        with patch.dict("sys.modules", {"autonomy_gates": None}):
            allowed, _ = sys.check_can_execute_tool("some_tool")
        assert allowed is True
