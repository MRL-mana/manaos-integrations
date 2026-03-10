"""
Unit tests for scripts/misc/startup_notification.py
"""
import sys
from unittest.mock import MagicMock, patch, call

import pytest

import types

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.UNIFIED_API_PORT = 9502  # type: ignore
sys.modules["_paths"] = _paths_mod
# manaos_integrations._paths もモック
_mi_paths = types.ModuleType("manaos_integrations._paths")
_mi_paths.UNIFIED_API_PORT = 9502  # type: ignore
_mi_mod = types.ModuleType("manaos_integrations")
_mi_mod._paths = _mi_paths  # type: ignore
sys.modules["manaos_integrations"] = _mi_mod
sys.modules["manaos_integrations._paths"] = _mi_paths

# notification_system モック（types.ModuleType でpytest_pluginsを避ける）
_ns_instance = MagicMock()
_ns_instance.slack_webhook_url = None
_ns_instance.send_slack = MagicMock()
_ns_cls = MagicMock(return_value=_ns_instance)

_ns_mod = types.ModuleType("notification_system")
_ns_mod.NotificationSystem = _ns_cls  # type: ignore
sys.modules["notification_system"] = _ns_mod

# dotenv は不要
sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))

import scripts.misc.startup_notification as sn


# ── TestWaitForReady ───────────────────────────────────────────────────────
class TestWaitForReady:
    def test_returns_json_when_ready(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"status": "ok"}
        with patch("scripts.misc.startup_notification.requests") as mock_requests, \
             patch("scripts.misc.startup_notification.time") as mock_time:
            mock_requests.get.return_value = mock_resp
            mock_time.time.side_effect = [0, 1]  # start, first check
            result = sn.wait_for_ready(max_wait=120, poll_interval=5)
        assert result == {"status": "ok"}

    def test_returns_none_on_timeout(self):
        with patch("scripts.misc.startup_notification.requests") as mock_requests, \
             patch("scripts.misc.startup_notification.time") as mock_time:
            mock_requests.get.side_effect = Exception("refused")
            # max_wait=1, 超えるまで繰り返す
            mock_time.time.side_effect = [0, 0.5, 1.5]  # 3rd call exceeds max_wait=1
            mock_time.sleep = MagicMock()
            result = sn.wait_for_ready(max_wait=1, poll_interval=1)
        assert result is None

    def test_returns_none_on_non_200(self):
        mock_resp = MagicMock(status_code=503)
        with patch("scripts.misc.startup_notification.requests") as mock_requests, \
             patch("scripts.misc.startup_notification.time") as mock_time:
            mock_requests.get.return_value = mock_resp
            mock_time.time.side_effect = [0, 0.5, 1.5]
            mock_time.sleep = MagicMock()
            result = sn.wait_for_ready(max_wait=1, poll_interval=1)
        assert result is None


# ── TestSendStartupReport ──────────────────────────────────────────────────
class TestSendStartupReport:
    def test_sends_message_when_ready(self):
        ready_data = {
            "status": "healthy",
            "integrations": {"svc_a": True, "svc_b": False},
            "readiness_checks": {
                "memory_db": {"status": "ok"},
                "obsidian_path": {"status": "ok"},
                "notification_hub": {"status": "warning"},
                "llm_routing": {"status": "ok"},
                "image_stock": {"status": "error"},
            },
        }
        ns_mock = MagicMock()
        ns_mock.send_slack = MagicMock()
        with patch("scripts.misc.startup_notification.notification_system", ns_mock), \
             patch("scripts.misc.startup_notification.wait_for_ready", return_value=ready_data):
            sn.send_startup_report()
        ns_mock.send_slack.assert_called_once()
        msg = ns_mock.send_slack.call_args[0][0]
        assert "manaOS" in msg

    def test_sends_timeout_message_when_not_ready(self):
        ns_mock = MagicMock()
        ns_mock.send_slack = MagicMock()
        with patch("scripts.misc.startup_notification.notification_system", ns_mock), \
             patch("scripts.misc.startup_notification.wait_for_ready", return_value=None):
            sn.send_startup_report()
        ns_mock.send_slack.assert_called_once()
        msg = ns_mock.send_slack.call_args[0][0]
        assert "タイムアウト" in msg or "120" in msg

    def test_does_nothing_when_no_notification_system(self, capsys):
        with patch("scripts.misc.startup_notification.notification_system", None):
            sn.send_startup_report()
        captured = capsys.readouterr()
        assert "利用できません" in captured.out

    def test_counts_available_integrations_correctly(self):
        ready_data = {
            "status": "healthy",
            "integrations": {"a": True, "b": True, "c": False},
            "readiness_checks": {},
        }
        ns_mock = MagicMock()
        with patch("scripts.misc.startup_notification.notification_system", ns_mock), \
             patch("scripts.misc.startup_notification.wait_for_ready", return_value=ready_data):
            sn.send_startup_report()
        msg = ns_mock.send_slack.call_args[0][0]
        assert "2/3" in msg
