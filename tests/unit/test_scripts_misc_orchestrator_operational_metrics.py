"""
Unit tests for scripts/misc/orchestrator_operational_metrics.py
"""
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

import pytest
import scripts.misc.orchestrator_operational_metrics as oom


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """テスト間でグローバル状態をリセット＋ファイルI/O を tmp_path に向ける"""
    oom._status_counts.clear()
    oom._error_code_counts.clear()
    oom._portal_timeout_count = 0
    oom._portal_timeout_timestamps.clear()
    oom._recent_results.clear()
    oom._last_notified.clear()
    oom._last_notified_loaded = False
    oom._last_notified_path = tmp_path / "orchestrator_alerts.json"
    yield
    oom._status_counts.clear()
    oom._error_code_counts.clear()
    oom._portal_timeout_count = 0
    oom._portal_timeout_timestamps.clear()
    oom._recent_results.clear()
    oom._last_notified.clear()
    oom._last_notified_loaded = False


# ── TestRecordResult ───────────────────────────────────────────────────────
class TestRecordResult:
    def test_increments_status_count(self):
        oom.record_result("ok")
        assert oom._status_counts["ok"] == 1

    def test_multiple_calls_accumulate(self):
        oom.record_result("ok")
        oom.record_result("ok")
        oom.record_result("error")
        assert oom._status_counts["ok"] == 2
        assert oom._status_counts["error"] == 1

    def test_records_error_code(self):
        oom.record_result("tool_error", error_code="AUTH_EXPIRED")
        assert oom._error_code_counts["AUTH_EXPIRED"] == 1

    def test_no_error_code_skip(self):
        oom.record_result("tool_error")
        assert len(oom._error_code_counts) == 0

    def test_appends_to_recent_results(self):
        oom.record_result("ok")
        assert len(oom._recent_results) == 1
        ts, st, ec = oom._recent_results[0]
        assert st == "ok"
        assert ec == ""

    def test_error_code_in_recent_results(self):
        oom.record_result("tool_error", error_code="TIMEOUT")
        ts, st, ec = oom._recent_results[0]
        assert ec == "TIMEOUT"


# ── TestRecordPortalTimeout ────────────────────────────────────────────────
class TestRecordPortalTimeout:
    def test_increments_count(self):
        oom.record_portal_timeout()
        assert oom._portal_timeout_count == 1

    def test_multiple_times(self):
        oom.record_portal_timeout()
        oom.record_portal_timeout()
        assert oom._portal_timeout_count == 2

    def test_timestamps_recorded(self):
        oom.record_portal_timeout()
        assert len(oom._portal_timeout_timestamps) == 1


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_returns_dict(self):
        assert isinstance(oom.get_stats(), dict)

    def test_required_keys(self):
        stats = oom.get_stats()
        for key in ("status", "error_code", "portal_timeout_total",
                    "portal_timeout_last_5min", "last_5min_by_status", "updated_at"):
            assert key in stats

    def test_status_reflects_records(self):
        oom.record_result("ok")
        oom.record_result("error")
        stats = oom.get_stats()
        assert stats["status"]["ok"] == 1
        assert stats["status"]["error"] == 1

    def test_portal_timeout_total(self):
        oom.record_portal_timeout()
        oom.record_portal_timeout()
        assert oom.get_stats()["portal_timeout_total"] == 2

    def test_portal_timeout_last_5min_includes_recent(self):
        oom.record_portal_timeout()
        assert oom.get_stats()["portal_timeout_last_5min"] == 1

    def test_updated_at_is_iso_format(self):
        stats = oom.get_stats()
        datetime.fromisoformat(stats["updated_at"])  # raises if invalid


# ── TestSuppressionKey ─────────────────────────────────────────────────────
class TestSuppressionKey:
    def test_portal_timeout_key(self):
        key = oom._suppression_key("error", None, portal_timeout=True)
        assert key == "portal_timeout"

    def test_tool_error_with_code(self):
        key = oom._suppression_key("tool_error", "AUTH_EXPIRED", portal_timeout=False)
        assert key == "tool_error:AUTH_EXPIRED"

    def test_plain_status(self):
        key = oom._suppression_key("error", None, portal_timeout=False)
        assert key == "error"


# ── TestShouldNotify ───────────────────────────────────────────────────────
class TestShouldNotify:
    def test_ok_never_notifies(self):
        assert oom.should_notify("ok") is False

    def test_skill_not_found_never_notifies(self):
        assert oom.should_notify("skill_not_found") is False

    def test_rate_limited_not_notifies(self):
        assert oom.should_notify("tool_error", error_code="RATE_LIMITED") is False

    def test_error_first_call_notifies(self):
        assert oom.should_notify("error") is True

    def test_error_second_call_suppressed(self):
        oom.should_notify("error")  # first → notified
        assert oom.should_notify("error") is False  # suppressed

    def test_portal_timeout_below_threshold_no_notify(self):
        # 2 timeouts, threshold=3 → no notify
        oom.record_portal_timeout()
        oom.record_portal_timeout()
        assert oom.should_notify("error", portal_timeout=True) is False

    def test_tool_error_auth_expired_notifies(self):
        assert oom.should_notify("tool_error", error_code="AUTH_EXPIRED") is True

    def test_suppression_different_codes_independent(self):
        oom.should_notify("tool_error", error_code="AUTH_EXPIRED")
        # Different code should still notify
        assert oom.should_notify("tool_error", error_code="DEVICE_UNREACHABLE") is True


# ── TestFormatSlackMessage ─────────────────────────────────────────────────
class TestFormatSlackMessage:
    def test_contains_status(self):
        msg = oom._format_slack_message("error", None, None, None, None, None)
        assert "[error]" in msg

    def test_contains_error_code(self):
        msg = oom._format_slack_message("tool_error", "AUTH_EXPIRED", None, None, None, None)
        assert "AUTH_EXPIRED" in msg

    def test_query_truncated(self):
        long_q = "x" * 100
        msg = oom._format_slack_message("error", None, long_q, None, None, None)
        assert "..." in msg

    def test_action_hint_included(self):
        msg = oom._format_slack_message("error", None, None, None, None, None, "re-try")
        assert "re-try" in msg

    def test_portal_trace_id_included(self):
        msg = oom._format_slack_message("error", None, None, "trace123", None, None)
        assert "trace123" in msg


# ── TestNotifySlack ────────────────────────────────────────────────────────
class TestNotifySlack:
    def test_no_webhook_no_slack_integration_returns_false(self, monkeypatch):
        monkeypatch.setattr(oom, "SLACK_WEBHOOK_URL", "")
        result = oom.notify_slack("error")
        assert result is False

    def test_webhook_called_on_success(self, monkeypatch):
        monkeypatch.setattr(oom, "SLACK_WEBHOOK_URL", "http://mock-webhook.example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.post", return_value=mock_resp):
            result = oom.notify_slack("error")
        assert result is True


# ── TestRecordAndMaybeAlert ────────────────────────────────────────────────
class TestRecordAndMaybeAlert:
    def test_portal_timeout_increments_count(self):
        oom.record_and_maybe_alert({}, is_portal_timeout=True)
        assert oom._portal_timeout_count == 1

    def test_records_status_from_body(self):
        oom.record_and_maybe_alert({"status": "ok"})
        assert oom._status_counts["ok"] == 1

    def test_records_error_code_from_body(self):
        body = {
            "status": "tool_error",
            "result": {"error_code": "AUTH_EXPIRED"},
        }
        oom.record_and_maybe_alert(body)
        assert oom._error_code_counts["AUTH_EXPIRED"] == 1

    def test_ok_no_slack_call(self):
        with patch.object(oom, "notify_slack") as mock_notify:
            oom.record_and_maybe_alert({"status": "ok"})
            mock_notify.assert_not_called()

    def test_error_triggers_notify(self):
        with patch.object(oom, "notify_slack") as mock_notify:
            mock_notify.return_value = True
            oom.record_and_maybe_alert({"status": "error"})
            mock_notify.assert_called_once()
