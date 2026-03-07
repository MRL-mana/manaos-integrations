"""
Unit tests for scripts/misc/secretary_routines.py
"""
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# manaos_core_api は None でインポートさせるとエラーになるので MagicMock へ
# ただし MANAOS_API_AVAILABLE は ImportError パスに任せたいため None を設定
sys.modules.setdefault("manaos_core_api", None)

import pytest
from scripts.misc.secretary_routines import SecretaryRoutines


# ── helpers ───────────────────────────────────────────────────────────────

def _make_sr(tmp_path: Path) -> SecretaryRoutines:
    """ストレージを tmp_path に向けた SecretaryRoutines インスタンスを生成"""
    sr = SecretaryRoutines.__new__(SecretaryRoutines)
    sr.tasks_storage = tmp_path / "tasks.json"
    sr.schedule_storage = tmp_path / "schedule.json"
    sr.tasks_storage.parent.mkdir(parents=True, exist_ok=True)
    return sr


def _write_tasks(path: Path, tasks: list):
    path.write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")


def _write_schedule(path: Path, schedule: list):
    path.write_text(json.dumps(schedule, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def sr(tmp_path):
    return _make_sr(tmp_path)


# ── TestLoadTasks ─────────────────────────────────────────────────────────
class TestLoadTasks:
    def test_empty_when_no_file(self, sr):
        assert sr._load_tasks() == []

    def test_loads_existing(self, sr):
        _write_tasks(sr.tasks_storage, [{"id": "t1", "title": "Task1"}])
        tasks = sr._load_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "t1"


# ── TestSaveTasks ─────────────────────────────────────────────────────────
class TestSaveTasks:
    def test_saves_and_reloads(self, sr):
        tasks = [{"id": "t2", "title": "Task2"}]
        sr._save_tasks(tasks)
        reloaded = sr._load_tasks()
        assert reloaded == tasks


# ── TestLoadSchedule ──────────────────────────────────────────────────────
class TestLoadSchedule:
    def test_empty_when_no_file(self, sr):
        assert sr._load_schedule() == []

    def test_loads_existing(self, sr):
        _write_schedule(sr.schedule_storage, [{"date": "2026-01-01", "title": "Meeting"}])
        schedule = sr._load_schedule()
        assert len(schedule) == 1


# ── TestGetTodaySchedule ──────────────────────────────────────────────────
class TestGetTodaySchedule:
    def test_returns_today_items(self, sr):
        today = datetime.now().date().isoformat()
        _write_schedule(sr.schedule_storage, [
            {"date": today, "time": "09:00", "title": "朝会"},
            {"date": "2020-01-01", "time": "10:00", "title": "古い予定"},
        ])
        result = sr._get_today_schedule()
        assert len(result) == 1
        assert result[0]["title"] == "朝会"

    def test_sorted_by_time(self, sr):
        today = datetime.now().date().isoformat()
        _write_schedule(sr.schedule_storage, [
            {"date": today, "time": "14:00", "title": "B"},
            {"date": today, "time": "09:00", "title": "A"},
        ])
        result = sr._get_today_schedule()
        assert result[0]["title"] == "A"
        assert result[1]["title"] == "B"


# ── TestGetTop3Tasks ──────────────────────────────────────────────────────
class TestGetTop3Tasks:
    def test_returns_top_3(self, sr):
        _write_tasks(sr.tasks_storage, [
            {"title": "T1", "priority": 3, "completed": False},
            {"title": "T2", "priority": 1, "completed": False},
            {"title": "T3", "priority": 2, "completed": False},
            {"title": "T4", "priority": 5, "completed": False},
        ])
        top3 = sr._get_top3_tasks()
        assert len(top3) == 3
        assert top3[0]["title"] == "T4"  # 優先度5

    def test_excludes_completed(self, sr):
        _write_tasks(sr.tasks_storage, [
            {"title": "Done", "priority": 10, "completed": True},
            {"title": "Todo", "priority": 5, "completed": False},
        ])
        top3 = sr._get_top3_tasks()
        assert all(not t.get("completed") for t in top3)

    def test_empty_tasks(self, sr):
        assert sr._get_top3_tasks() == []


# ── TestGetYesterdayLogDiff ───────────────────────────────────────────────
class TestGetYesterdayLogDiff:
    def test_fallback_when_api_unavailable(self, sr):
        result = sr._get_yesterday_log_diff()
        # MANAOS_API_AVAILABLE = False のフォールバック
        assert "total" in result
        assert result["total"] == 0


# ── TestGetLatestNews ─────────────────────────────────────────────────────
class TestGetLatestNews:
    def test_fallback_when_api_unavailable(self, sr):
        result = sr._get_latest_news(topics=["Python"])
        assert "results" in result
        assert result["count"] == 0


# ── TestAnalyzeIncompleteTask ─────────────────────────────────────────────
class TestAnalyzeIncompleteTask:
    def test_time_category(self, sr):
        task = {"title": "タスク", "reason": "時間が足りなかった"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "時間不足"

    def test_unclear_category(self, sr):
        task = {"title": "タスク", "reason": "内容が不明確だった"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "不明確"

    def test_dependency_category(self, sr):
        task = {"title": "タスク", "reason": "依存するAPIを待っている"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "依存待ち"

    def test_motivation_category(self, sr):
        task = {"title": "タスク", "reason": "気力が出ない"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "気力不足"

    def test_hard_category(self, sr):
        task = {"title": "タスク", "reason": "難しすぎて進まない"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "難しすぎ"

    def test_other_category(self, sr):
        task = {"title": "タスク", "reason": "特別な理由"}
        result = sr._analyze_incomplete_task(task)
        assert result["reason_category"] == "その他"

    def test_no_reason_fallback(self, sr):
        task = {"title": "タスク"}
        result = sr._analyze_incomplete_task(task)
        assert "reason_category" in result


# ── TestCheckProgress ─────────────────────────────────────────────────────
class TestCheckProgress:
    def test_empty(self, sr):
        p = sr._check_progress()
        assert p["total"] == 0
        assert p["completed"] == 0
        assert p["completion_rate"] == 0

    def test_completion_rate(self, sr):
        _write_tasks(sr.tasks_storage, [
            {"title": "A", "completed": True},
            {"title": "B", "completed": True},
            {"title": "C", "completed": False},
            {"title": "D", "completed": False},
        ])
        p = sr._check_progress()
        assert p["total"] == 4
        assert p["completed"] == 2
        assert abs(p["completion_rate"] - 50.0) < 0.01


# ── TestMorningRoutine ────────────────────────────────────────────────────
class TestMorningRoutine:
    def test_returns_required_keys(self, sr):
        result = sr.morning_routine()
        for k in ("schedule", "tasks", "log_diff", "latest_news", "report"):
            assert k in result

    def test_report_is_string(self, sr):
        result = sr.morning_routine()
        assert isinstance(result["report"], str)
        assert "朝のルーチン" in result["report"]


# ── TestNoonRoutine ───────────────────────────────────────────────────────
class TestNoonRoutine:
    def test_returns_required_keys(self, sr):
        result = sr.noon_routine()
        for k in ("progress", "report"):
            assert k in result

    def test_report_contains_noon(self, sr):
        result = sr.noon_routine()
        assert "昼のルーチン" in result["report"]


# ── TestPrepareTomorrow ───────────────────────────────────────────────────
class TestPrepareTomorrow:
    def test_structure(self, sr):
        result = sr._prepare_tomorrow()
        assert "schedule" in result
        assert "tasks" in result

    def test_top_3_tasks_max(self, sr):
        _write_tasks(sr.tasks_storage, [
            {"title": f"T{i}", "priority": i, "completed": False} for i in range(10)
        ])
        result = sr._prepare_tomorrow()
        assert len(result["tasks"]) <= 3


# ── TestEveningRoutine ────────────────────────────────────────────────────
class TestEveningRoutine:
    def test_returns_required_keys(self, sr):
        result = sr.evening_routine()
        for k in ("daily_report", "tomorrow_prep", "report"):
            assert k in result

    def test_report_contains_evening(self, sr):
        result = sr.evening_routine()
        assert "夜のルーチン" in result["report"]
