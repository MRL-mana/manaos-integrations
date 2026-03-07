"""Unit tests for tools/manaosctl.py pure helpers."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import manaosctl as ctl

# ─────────────────────────────────────────────────────────────────────────────
# c() — ANSI カラーラッパー
# ─────────────────────────────────────────────────────────────────────────────

class TestC:
    def test_wraps_with_color_and_reset(self):
        result = ctl.c("hello", ctl.RED)
        assert result.startswith(ctl.RED)
        assert result.endswith(ctl.RESET)
        assert "hello" in result

    def test_empty_color_string(self):
        result = ctl.c("text", "")
        assert result == f"text{ctl.RESET}"

    def test_cyan_wrapping(self):
        result = ctl.c("service", ctl.CYAN)
        assert ctl.CYAN in result
        assert ctl.RESET in result

    def test_bold_wrapping(self):
        result = ctl.c("header", ctl.BOLD)
        assert ctl.BOLD in result


# ─────────────────────────────────────────────────────────────────────────────
# send_notify() — Slack / ntfy フォールバック通知
# ─────────────────────────────────────────────────────────────────────────────

def _mock_response(status: int):
    """urllib.request.urlopen のコンテキストマネージャ互換モック。"""
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestSendNotify:
    def test_slack_path_returns_slack(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.delenv("NTFY_TOPIC", raising=False)
        # REPO_ROOT/.env が存在しない tmp_path に向ける
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        resp = _mock_response(200)
        with patch("urllib.request.urlopen", return_value=resp):
            result = ctl.send_notify("Title", "Message")
        assert result == "slack"

    def test_slack_5xx_falls_to_ntfy(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        slack_resp = _mock_response(500)
        ntfy_resp = _mock_response(200)
        responses = iter([slack_resp, ntfy_resp])

        with patch("urllib.request.urlopen", side_effect=lambda *a, **kw: next(responses)):
            result = ctl.send_notify("T", "M")
        assert result == "ntfy"

    def test_no_slack_url_goes_to_ntfy(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.setenv("NTFY_TOPIC", "my-topic")
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        resp = _mock_response(200)
        with patch("urllib.request.urlopen", return_value=resp):
            result = ctl.send_notify("Alert", "body text")
        assert result == "ntfy"

    def test_all_fail_returns_failed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        with patch("urllib.request.urlopen", side_effect=OSError("network error")):
            result = ctl.send_notify("T", "M")
        assert result == "failed"

    def test_slack_url_from_env_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text("SLACK_WEBHOOK_URL=https://hooks.slack.com/env\n", encoding="utf-8")

        resp = _mock_response(200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_open:
            result = ctl.send_notify("Test", "From env file")

        assert result == "slack"
        # Slack URL が呼ばれたことを検証
        call_url = mock_open.call_args[0][0].full_url
        assert "hooks.slack.com" in call_url

    def test_ntfy_topic_from_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.setenv("NTFY_TOPIC", "custom-topic")
        monkeypatch.setattr(ctl, "REPO_ROOT", tmp_path)

        resp = _mock_response(200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_open:
            result = ctl.send_notify("T", "M")

        assert result == "ntfy"
        call_url = mock_open.call_args[0][0].full_url
        assert "custom-topic" in call_url
