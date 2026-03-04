"""
tests/test_secretary_system.py
SecretarySystem の単体テスト

対象: scripts/misc/secretary_system.py
- ReminderType enum
- Reminder dataclass
- Report dataclass
- SecretarySystem 初期化（SQLite DB）
- add_reminder / get_due_reminders / complete_reminder
- _save_report / get_reports
- generate_daily_report（HTTP 失敗時のフォールバック）
"""

import json
import pytest
from datetime import datetime, timedelta
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch, MagicMock


# =====================================================================
# sys.path は conftest.py が設定済み
# =====================================================================
from scripts.misc.secretary_system import (
    ReminderType,
    Reminder,
    Report,
    SecretarySystem,
)


# ----------------------------------------------------------------------
# ヘルパー
# ----------------------------------------------------------------------

def make_secretary(tmp_path: Path) -> SecretarySystem:
    """ファイル I/O を tmp_path に誘導した SecretarySystem を返す。"""
    return SecretarySystem(
        orchestrator_url="http://127.0.0.1:9999",
        db_path=tmp_path / "secretary_test.db",
        config_path=tmp_path / "secretary_config.json",  # 存在しない → デフォルト設定
    )


def make_reminder(
    rid: str = "r001",
    title: str = "テストリマインダー",
    scheduled_time: str | None = None,
    reminder_type: ReminderType = ReminderType.ONCE,
) -> Reminder:
    if scheduled_time is None:
        # デフォルトは 1 分前（= 期限切れ状態）
        scheduled_time = (datetime.now() - timedelta(minutes=1)).isoformat()
    return Reminder(
        reminder_id=rid,
        title=title,
        description="テスト用",
        scheduled_time=scheduled_time,
        reminder_type=reminder_type,
    )


# ======================================================================
# 1. ReminderType enum
# ======================================================================

class TestReminderType:
    def test_once_value(self) -> None:
        assert ReminderType.ONCE.value == "once"

    def test_all_types_present(self) -> None:
        for name in ("ONCE", "DAILY", "WEEKLY", "MONTHLY", "CUSTOM"):
            assert hasattr(ReminderType, name)

    def test_isinstance_str(self) -> None:
        assert isinstance(ReminderType.DAILY, str)


# ======================================================================
# 2. Reminder dataclass
# ======================================================================

class TestReminder:
    def test_created_at_auto_set(self) -> None:
        r = make_reminder()
        assert r.created_at != ""

    def test_defaults(self) -> None:
        r = make_reminder()
        assert r.enabled is True
        assert r.completed is False
        assert r.completed_at is None

    def test_asdict_roundtrip(self) -> None:
        r = make_reminder("r_rt")
        d = asdict(r)
        reconstructed = Reminder(**d)
        assert reconstructed.reminder_id == r.reminder_id


# ======================================================================
# 3. Report dataclass
# ======================================================================

class TestReport:
    def test_metadata_default_empty_dict(self) -> None:
        rep = Report(
            report_id="rep001",
            report_type="daily",
            title="タイトル",
            content="content",
            generated_at=datetime.now().isoformat(),
        )
        assert rep.metadata == {}

    def test_metadata_explicit(self) -> None:
        rep = Report(
            report_id="rep002",
            report_type="daily",
            title="タイトル",
            content="content",
            generated_at=datetime.now().isoformat(),
            metadata={"key": "value"},
        )
        assert rep.metadata["key"] == "value"


# ======================================================================
# 4. SecretarySystem 初期化
# ======================================================================

class TestSecretarySystemInit:
    def test_db_file_created(self, tmp_path: Path) -> None:
        make_secretary(tmp_path)
        assert (tmp_path / "secretary_test.db").exists()

    def test_default_config(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        assert "auto_report_enabled" in sys.config
        assert sys.config["report_schedule"] == "daily"


# ======================================================================
# 5. add_reminder / get_due_reminders
# ======================================================================

class TestAddAndGetReminders:
    def test_add_then_due_returns_it(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        r = make_reminder("r_due")
        sys.add_reminder(r)
        due = sys.get_due_reminders()
        ids = [x.reminder_id for x in due]
        assert "r_due" in ids

    def test_future_reminder_not_due(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        r = make_reminder("r_future", scheduled_time=future)
        sys.add_reminder(r)
        due = sys.get_due_reminders()
        ids = [x.reminder_id for x in due]
        assert "r_future" not in ids

    def test_multiple_due(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        for i in range(3):
            sys.add_reminder(make_reminder(f"r_m{i}"))
        assert len(sys.get_due_reminders()) >= 3

    def test_disabled_reminder_not_due(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        r = make_reminder("r_disabled")
        r.enabled = False
        sys.add_reminder(r)
        due_ids = [x.reminder_id for x in sys.get_due_reminders()]
        assert "r_disabled" not in due_ids


# ======================================================================
# 6. complete_reminder
# ======================================================================

class TestCompleteReminder:
    def test_complete_removes_from_due(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        r = make_reminder("r_complete")
        sys.add_reminder(r)
        sys.complete_reminder("r_complete")
        due_ids = [x.reminder_id for x in sys.get_due_reminders()]
        assert "r_complete" not in due_ids

    def test_complete_nonexistent_no_error(self, tmp_path: Path) -> None:
        """存在しない ID を complete しても例外が出ない"""
        sys = make_secretary(tmp_path)
        sys.complete_reminder("nonexistent_id_xyz")  # should not raise


# ======================================================================
# 7. _save_report / get_reports
# ======================================================================

class TestSaveAndGetReports:
    def test_empty_reports_on_init(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        assert sys.get_reports() == []

    def test_save_and_get_report(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        rep = Report(
            report_id="rep_test",
            report_type="daily",
            title="テスト報告",
            content="内容",
            generated_at=datetime.now().isoformat(),
            metadata={"note": "unit_test"},
        )
        sys._save_report(rep)
        reports = sys.get_reports()
        assert len(reports) == 1
        assert reports[0].report_id == "rep_test"
        assert reports[0].metadata["note"] == "unit_test"

    def test_filter_by_type(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        for rtype in ("daily", "weekly", "daily"):
            rep = Report(
                report_id=f"rep_{rtype}_{id(rtype)}",
                report_type=rtype,
                title="t",
                content="c",
                generated_at=datetime.now().isoformat(),
            )
            sys._save_report(rep)
        weeklies = sys.get_reports(report_type="weekly")
        assert all(r.report_type == "weekly" for r in weeklies)

    def test_limit_respected(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        for i in range(10):
            sys._save_report(Report(
                report_id=f"rep_{i:03d}",
                report_type="daily",
                title="t",
                content="c",
                generated_at=datetime.now().isoformat(),
            ))
        assert len(sys.get_reports(limit=3)) == 3


# ======================================================================
# 8. generate_daily_report（HTTP 失敗時のフォールバック）
# ======================================================================

class TestGenerateDailyReport:
    def test_returns_report_on_http_error(self, tmp_path: Path) -> None:
        """Orchestrator が落ちていても Report オブジェクトが返る"""
        sys = make_secretary(tmp_path)
        report = sys.generate_daily_report()
        assert isinstance(report, Report)
        assert report.report_type == "daily"
        assert report.title != ""

    def test_report_id_format(self, tmp_path: Path) -> None:
        """HTTP エラー時でも report_id が日付フォーマットになっている"""
        sys = make_secretary(tmp_path)
        report = sys.generate_daily_report()
        # report_YYYYMMDD 形式か、または空でないことを確認
        assert report.report_id.startswith("report_")

    def test_format_daily_report_contains_summary(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        content = sys._format_daily_report([])
        assert "実行サマリー" in content

    def test_format_daily_report_with_history(self, tmp_path: Path) -> None:
        sys = make_secretary(tmp_path)
        history = [{"status": "success", "intent_type": "test_intent"}]
        content = sys._format_daily_report(history)
        assert "test_intent" in content
