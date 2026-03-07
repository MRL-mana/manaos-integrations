"""
Unit tests for scripts/misc/comfyui_monitor.py
"""
import sys
import json
from unittest.mock import MagicMock, patch

# _paths モック
_paths_mod = MagicMock()
_paths_mod.COMFYUI_PORT = 8188
sys.modules.setdefault("_paths", _paths_mod)

import pytest
from scripts.misc.comfyui_monitor import check_comfyui_status, send_slack


# ── helpers ────────────────────────────────────────────────────────────────
def _make_urlopen(body_bytes: bytes, status: int = 200):
    """urllib.request.urlopen の mock レスポンス"""
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = body_bytes
    resp.status = status
    return resp


# ── TestCheckComfyUIStatus ─────────────────────────────────────────────────
class TestCheckComfyUIStatus:
    def test_returns_true_on_success(self):
        stats_body = json.dumps({"system": {}}).encode()
        queue_body = json.dumps({"queue_running": [], "queue_pending": []}).encode()

        stats_resp = _make_urlopen(stats_body)
        queue_resp = _make_urlopen(queue_body)
        side_effects = [stats_resp, queue_resp]

        with patch("urllib.request.urlopen", side_effect=side_effects):
            ok, msg, queue_len = check_comfyui_status()
        assert ok is True

    def test_returns_queue_length(self):
        stats_body = json.dumps({}).encode()
        queue_body = json.dumps(
            {"queue_running": [{"id": 1}], "queue_pending": [{"id": 2}, {"id": 3}]}
        ).encode()

        with patch("urllib.request.urlopen", side_effect=[
            _make_urlopen(stats_body),
            _make_urlopen(queue_body),
        ]):
            ok, msg, queue_len = check_comfyui_status()
        assert ok is True
        assert queue_len == 3

    def test_returns_false_on_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            ok, msg, queue_len = check_comfyui_status()
        assert ok is False
        assert queue_len == 0
        assert "connection refused" in msg

    def test_queue_zero_when_queue_fails(self):
        stats_body = json.dumps({}).encode()
        with patch("urllib.request.urlopen", side_effect=[
            _make_urlopen(stats_body),
            OSError("queue endpoint down"),
        ]):
            ok, msg, queue_len = check_comfyui_status()
        assert ok is True
        assert queue_len == 0

    def test_msg_ok_on_success(self):
        with patch("urllib.request.urlopen", side_effect=[
            _make_urlopen(b"{}"),
            _make_urlopen(b'{"queue_running":[], "queue_pending":[]}'),
        ]):
            ok, msg, _ = check_comfyui_status()
        assert ok is True
        assert msg != ""


# ── TestSendSlack ──────────────────────────────────────────────────────────
class TestSendSlack:
    def test_returns_false_without_webhook(self):
        result = send_slack("hello", webhook_url="")
        assert result is False

    def test_returns_true_on_success(self):
        resp = _make_urlopen(b"ok")
        with patch("urllib.request.urlopen", return_value=resp):
            result = send_slack("alert!", webhook_url="https://hooks.slack.com/test")
        assert result is True

    def test_returns_false_on_exception(self):
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = send_slack("msg", webhook_url="https://hooks.slack.com/test")
        assert result is False

    def test_none_webhook_uses_global(self):
        # webhook_url=None → SLACK_WEBHOOK_URL (empty by default) → False
        result = send_slack("msg", webhook_url=None)
        assert result is False
