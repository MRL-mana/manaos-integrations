"""Unit tests for tools/events.py — offline, no Slack/services required."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import events as events_mod
from events import emit, read_events


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _patch_log(tmp_path: Path):
    """Context manager: redirect EVENT_LOG and LOG_DIR to a temp directory."""
    log_file = tmp_path / "events.jsonl"
    return patch.multiple(
        events_mod,
        EVENT_LOG=log_file,
        LOG_DIR=tmp_path,
    )


# ===========================================================================
# emit()
# ===========================================================================

class TestEmit:
    def test_creates_jsonl_file(self, tmp_path):
        with _patch_log(tmp_path):
            emit("startup")
        assert (tmp_path / "events.jsonl").exists()

    def test_record_has_required_fields(self, tmp_path):
        with _patch_log(tmp_path):
            emit("service_up", service="llm_routing", detail="healed")
        lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["event"] == "service_up"
        assert obj["service"] == "llm_routing"
        assert obj["detail"] == "healed"
        assert "time" in obj

    def test_appends_multiple_records(self, tmp_path):
        with _patch_log(tmp_path):
            emit("startup")
            emit("service_down", service="comfyui")
            emit("heal_ok")
        lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_none_service_and_detail_become_empty_string(self, tmp_path):
        with _patch_log(tmp_path):
            emit("policy")
        obj = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").strip())
        assert obj["service"] == ""
        assert obj["detail"] == ""

    def test_source_field_stored(self, tmp_path):
        with _patch_log(tmp_path):
            emit("startup", source="manaosctl.py")
        obj = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").strip())
        assert obj["source"] == "manaosctl.py"

    def test_time_format_is_iso_like(self, tmp_path):
        with _patch_log(tmp_path):
            emit("startup")
        obj = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").strip())
        # e.g. "2026-03-07T12:00:00"
        assert "T" in obj["time"]
        assert len(obj["time"]) == 19

    def test_slack_notify_events_fire_async(self, tmp_path):
        """Events in SLACK_NOTIFY_EVENTS should call _notify_slack_async."""
        with _patch_log(tmp_path), \
             patch("events._notify_slack_async") as mock_notify:
            emit("service_down", service="test-svc", detail="gone")
        mock_notify.assert_called_once_with("service_down", "test-svc", "gone")

    def test_non_slack_events_do_not_fire_async(self, tmp_path):
        with _patch_log(tmp_path), \
             patch("events._notify_slack_async") as mock_notify:
            emit("startup")
            emit("service_up", service="foo")
        mock_notify.assert_not_called()


# ===========================================================================
# read_events()
# ===========================================================================

class TestReadEvents:
    def test_returns_empty_when_no_file(self, tmp_path):
        with _patch_log(tmp_path):
            result = read_events()
        assert result == []

    def test_returns_all_records_when_under_limit(self, tmp_path):
        with _patch_log(tmp_path):
            for i in range(5):
                emit(f"event_{i}")
            result = read_events(n=50)
        assert len(result) == 5
        assert result[0]["event"] == "event_0"

    def test_returns_last_n_records(self, tmp_path):
        with _patch_log(tmp_path):
            for i in range(10):
                emit(f"event_{i}")
            result = read_events(n=3)
        assert len(result) == 3
        assert result[-1]["event"] == "event_9"

    def test_skips_malformed_json_lines(self, tmp_path):
        log_file = tmp_path / "events.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(
            '{"event": "good1"}\nNOT_JSON\n{"event": "good2"}\n',
            encoding="utf-8",
        )
        with _patch_log(tmp_path):
            result = read_events()
        events_names = [r["event"] for r in result]
        assert "good1" in events_names
        assert "good2" in events_names
        # malformed line should be skipped, not raise
        assert len(result) == 2

    def test_returns_list_of_dicts(self, tmp_path):
        with _patch_log(tmp_path):
            emit("service_up", service="memory")
            result = read_events(n=1)
        assert isinstance(result, list)
        assert isinstance(result[0], dict)


# ===========================================================================
# _maybe_rotate()
# ===========================================================================

class TestMaybeRotate:
    def test_no_rotate_when_below_threshold(self, tmp_path):
        log_file = tmp_path / "events.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # write 3 lines (well below ROTATE_AT=5000)
        log_file.write_text("\n".join(['{"event":"x"}'] * 3) + "\n", encoding="utf-8")
        with patch.multiple(events_mod, EVENT_LOG=log_file, LOG_DIR=tmp_path,
                            ROTATE_AT=5000):
            events_mod._maybe_rotate()
        assert log_file.exists()
        assert not (tmp_path / "events.1.jsonl").exists()

    def test_rotate_when_at_or_above_threshold(self, tmp_path):
        log_file = tmp_path / "events.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # write exactly ROTATE_AT lines
        rotate_at = 10
        log_file.write_text("\n".join(['{"event":"x"}'] * rotate_at) + "\n", encoding="utf-8")
        with patch.multiple(events_mod, EVENT_LOG=log_file, LOG_DIR=tmp_path,
                            ROTATE_AT=rotate_at):
            events_mod._maybe_rotate()
        # original file renamed away, rotated file exists
        assert not log_file.exists()
        assert (tmp_path / "events.1.jsonl").exists()

    def test_no_error_when_file_absent(self, tmp_path):
        with patch.multiple(events_mod, EVENT_LOG=tmp_path / "missing.jsonl",
                            LOG_DIR=tmp_path):
            events_mod._maybe_rotate()  # should not raise
