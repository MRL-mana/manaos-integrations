"""
Unit tests for scripts/misc/secretary_system.py
"""
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

sys.modules.setdefault("flask_cors", MagicMock())

_paths = MagicMock()
_paths.ORCHESTRATOR_PORT = 8100
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.secretary_system import (
    Reminder,
    ReminderType,
    Report,
    SecretarySystem,
)


@pytest.fixture
def ss(tmp_path):
    return SecretarySystem(
        db_path=tmp_path / "ss_test.db",
        config_path=tmp_path / "ss_config.json",
    )


def _past(minutes: int = 5) -> str:
    return (datetime.now() - timedelta(minutes=minutes)).isoformat()


def _future(minutes: int = 60) -> str:
    return (datetime.now() + timedelta(minutes=minutes)).isoformat()


# ── TestReminderType ───────────────────────────────────────────────────────
class TestReminderType:
    def test_values(self):
        assert ReminderType.ONCE.value == "once"
        assert ReminderType.DAILY.value == "daily"
        assert ReminderType.WEEKLY.value == "weekly"
        assert ReminderType.MONTHLY.value == "monthly"
        assert ReminderType.CUSTOM.value == "custom"

    def test_is_str_subclass(self):
        assert isinstance(ReminderType.ONCE, str)


# ── TestReminder ──────────────────────────────────────────────────────────
class TestReminder:
    def test_created_at_auto_set(self):
        r = Reminder(
            reminder_id="r1",
            title="test",
            description="desc",
            scheduled_time=_future(),
            reminder_type=ReminderType.ONCE,
        )
        assert r.created_at  # 空でない

    def test_default_enabled_true(self):
        r = Reminder(
            reminder_id="r2",
            title="t",
            description="d",
            scheduled_time=_future(),
            reminder_type=ReminderType.DAILY,
        )
        assert r.enabled is True
        assert r.completed is False


# ── TestReport ────────────────────────────────────────────────────────────
class TestReport:
    def test_metadata_defaults_to_empty_dict(self):
        rep = Report(
            report_id="rep1",
            report_type="daily",
            title="今日のレポート",
            content="本日の活動内容",
            generated_at=datetime.now().isoformat(),
        )
        assert rep.metadata == {}

    def test_explicit_metadata(self):
        rep = Report(
            report_id="rep2",
            report_type="weekly",
            title="Weekly",
            content="Content",
            generated_at="2026-01-01",
            metadata={"source": "auto"},
        )
        assert rep.metadata["source"] == "auto"


# ── TestInitDatabase ──────────────────────────────────────────────────────
class TestInitDatabase:
    def test_tables_created(self, ss):
        conn = sqlite3.connect(ss.db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "reminders" in tables
        assert "reports" in tables

    def test_idempotent(self, ss):
        # 2 回呼んでも壊れない
        ss._init_database()
        conn = sqlite3.connect(ss.db_path)
        count = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('reminders','reports')"
        ).fetchone()[0]
        conn.close()
        assert count == 2


# ── TestGetDefaultConfig ──────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_returns_dict_with_keys(self, ss):
        cfg = ss._get_default_config()
        assert cfg["auto_report_enabled"] is True
        assert cfg["report_schedule"] == "daily"
        assert cfg["reminder_check_interval_seconds"] == 60


# ── TestAddReminder ───────────────────────────────────────────────────────
class TestAddReminder:
    def test_inserts_and_returns(self, ss):
        r = Reminder("r_add1", "朝会", "朝のミーティング", _future(), ReminderType.DAILY)
        result = ss.add_reminder(r)
        assert result.reminder_id == "r_add1"

    def test_persisted_in_db(self, ss):
        r = Reminder("r_db1", "DB確認", "", _future(), ReminderType.ONCE)
        ss.add_reminder(r)
        conn = sqlite3.connect(ss.db_path)
        row = conn.execute(
            "SELECT reminder_id FROM reminders WHERE reminder_id=?", ("r_db1",)
        ).fetchone()
        conn.close()
        assert row is not None

    def test_upsert_updates_title(self, ss):
        r1 = Reminder("dup_r", "旧タイトル", "", _future(), ReminderType.ONCE)
        r2 = Reminder("dup_r", "新タイトル", "", _future(), ReminderType.ONCE)
        ss.add_reminder(r1)
        ss.add_reminder(r2)
        conn = sqlite3.connect(ss.db_path)
        row = conn.execute(
            "SELECT title FROM reminders WHERE reminder_id=?", ("dup_r",)
        ).fetchone()
        conn.close()
        assert row[0] == "新タイトル"


# ── TestGetDueReminders ───────────────────────────────────────────────────
class TestGetDueReminders:
    def test_empty_when_no_reminders(self, ss):
        assert ss.get_due_reminders() == []

    def test_returns_past_reminder(self, ss):
        r = Reminder("past_r", "Past", "", _past(10), ReminderType.ONCE)
        ss.add_reminder(r)
        due = ss.get_due_reminders()
        assert any(x.reminder_id == "past_r" for x in due)

    def test_excludes_future_reminder(self, ss):
        r = Reminder("future_r", "Future", "", _future(60), ReminderType.ONCE)
        ss.add_reminder(r)
        due = ss.get_due_reminders()
        assert all(x.reminder_id != "future_r" for x in due)

    def test_excludes_completed_reminder(self, ss):
        r = Reminder("done_r", "Done", "", _past(5), ReminderType.ONCE, completed=True)
        ss.add_reminder(r)
        due = ss.get_due_reminders()
        assert all(x.reminder_id != "done_r" for x in due)

    def test_excludes_disabled_reminder(self, ss):
        r = Reminder("off_r", "Off", "", _past(5), ReminderType.ONCE, enabled=False)
        ss.add_reminder(r)
        due = ss.get_due_reminders()
        assert all(x.reminder_id != "off_r" for x in due)
