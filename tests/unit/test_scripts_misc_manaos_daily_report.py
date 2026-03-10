"""
Unit tests for scripts/misc/manaos_daily_report.py
"""
import sys
import json
import types
import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────
# events (tools/events.py)
_events_mod = types.ModuleType("events")
_events_mod.read_events = MagicMock(return_value=[])  # type: ignore
_events_mod.emit = MagicMock()  # type: ignore
sys.modules.setdefault("events", _events_mod)

import scripts.misc.manaos_daily_report as dr


# ─────────────────────────────────────────────
# get_service_status
# ─────────────────────────────────────────────

class TestGetServiceStatus:
    def test_returns_services_from_subprocess(self):
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"services": [{"name": "svc1", "alive": True}]})
        with patch("subprocess.run", return_value=mock_result):
            result = dr.get_service_status()
        assert result == [{"name": "svc1", "alive": True}]

    def test_returns_empty_on_exception(self):
        with patch("subprocess.run", side_effect=RuntimeError("fail")):
            result = dr.get_service_status()
        assert result == []

    def test_returns_empty_on_invalid_json(self):
        mock_result = MagicMock()
        mock_result.stdout = "not json"
        with patch("subprocess.run", return_value=mock_result):
            result = dr.get_service_status()
        assert result == []


# ─────────────────────────────────────────────
# build_prompt
# ─────────────────────────────────────────────

class TestBuildPrompt:
    def test_contains_required_sections(self):
        events = [{"id": 1, "type": "error"}]
        services = [{"name": "svc1", "alive": True}, {"name": "svc2", "alive": False}]
        prompt = dr.build_prompt(events, services, 10)
        assert "サービス状態" in prompt
        assert "ManaOS" in prompt
        assert "svc2" in prompt  # down service

    def test_shows_down_count(self):
        services = [{"name": "a", "alive": False}, {"name": "b", "alive": True}]
        prompt = dr.build_prompt([], services, 5)
        assert "DOWN=1" in prompt

    def test_empty_events_message(self):
        prompt = dr.build_prompt([], [], 5)
        assert "イベントなし" in prompt

    def test_includes_history_when_summary_exists(self, tmp_path):
        summary = {"last_updated": "2026-01-01", "summary": "前回OK"}
        summary_file = tmp_path / "events.summary.json"
        summary_file.write_text(json.dumps(summary), encoding="utf-8")

        with patch.object(dr, "SUMMARY_JSON", summary_file):
            prompt = dr.build_prompt([], [], 5)

        assert "前回OK" in prompt

    def test_n_events_in_prompt(self):
        prompt = dr.build_prompt([], [], 42)
        assert "42" in prompt


# ─────────────────────────────────────────────
# call_llm
# ─────────────────────────────────────────────

class TestCallLlm:
    def test_returns_response_and_model(self):
        fake_response = json.dumps({"response": "All good", "model": "qwen2.5"}).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=mock_resp):
            text, model = dr.call_llm("test prompt")

        assert text == "All good"
        assert model == "qwen2.5"

    def test_returns_empty_strings_on_missing_keys(self):
        fake_response = json.dumps({}).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=mock_resp):
            text, model = dr.call_llm("prompt")

        assert text == ""
        assert model == "?"


# ─────────────────────────────────────────────
# save_report
# ─────────────────────────────────────────────

class TestSaveReport:
    def test_creates_file(self, tmp_path):
        with patch.object(dr, "ANALYSIS_DIR", tmp_path):
            path = dr.save_report("Report content", "gpt4")

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Report content" in content
        assert "gpt4" in content

    def test_filename_contains_timestamp(self, tmp_path):
        with patch.object(dr, "ANALYSIS_DIR", tmp_path):
            path = dr.save_report("x", "model")
        # YYYYMMDD_HHMM.txt pattern
        assert path.suffix == ".txt"
        assert "_" in path.stem


# ─────────────────────────────────────────────
# update_summary
# ─────────────────────────────────────────────

class TestUpdateSummary:
    def test_writes_summary_json(self, tmp_path):
        summary_file = tmp_path / "events.summary.json"
        services = [{"alive": True}, {"alive": False}, {"alive": True}]

        with patch.object(dr, "SUMMARY_JSON", summary_file):
            dr.update_summary("Total OK", "qwen", [{"e": 1}], services)

        assert summary_file.exists()
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert data["service_up"] == 2
        assert data["service_down"] == 1
        assert data["events_analyzed"] == 1
        assert data["model"] == "qwen"

    def test_uses_first_line_as_short_summary(self, tmp_path):
        summary_file = tmp_path / "events.summary.json"
        report = "Line one\nLine two\nLine three"

        with patch.object(dr, "SUMMARY_JSON", summary_file):
            dr.update_summary(report, "m", [], [])

        data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert data["summary"] == "Line one"


# ─────────────────────────────────────────────
# notify_slack
# ─────────────────────────────────────────────

class TestNotifySlack:
    def test_does_not_raise_on_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            dr.notify_slack("hello")  # Should not raise

    def test_calls_urlopen(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            dr.notify_slack("test message")

        mock_open.assert_called_once()
