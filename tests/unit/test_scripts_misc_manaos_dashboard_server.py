"""
Unit tests for scripts/misc/manaos_dashboard_server.py
"""
import sys
import json
import types
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────

# events (tools/events.py) はモック
_events_mod = types.ModuleType("events")
_events_mod.read_events = MagicMock(return_value=[{"id": 1}])  # type: ignore
sys.modules.setdefault("events", _events_mod)

import scripts.misc.manaos_dashboard_server as srv


# ─────────────────────────────────────────────
# _run_manaosctl
# ─────────────────────────────────────────────

class TestRunManaosctl:
    def test_returns_parsed_json_on_success(self):
        mock_result = MagicMock()
        mock_result.stdout = '{"status": "ok"}'
        mock_result.stderr = ""

        with patch("scripts.misc.manaos_dashboard_server.subprocess.run",
                   return_value=mock_result) as mock_run:
            result = srv._run_manaosctl("status")

        assert result == {"status": "ok"}
        # --json が引数に含まれること
        called_args = mock_run.call_args[0][0]
        assert "--json" in called_args

    def test_returns_error_dict_on_invalid_json(self):
        mock_result = MagicMock()
        mock_result.stdout = "not valid json"
        mock_result.stderr = "something went wrong"

        with patch("scripts.misc.manaos_dashboard_server.subprocess.run",
                   return_value=mock_result):
            result = srv._run_manaosctl("status")

        assert "error" in result

    def test_passes_additional_args(self):
        mock_result = MagicMock()
        mock_result.stdout = "{}"
        mock_result.stderr = ""

        with patch("scripts.misc.manaos_dashboard_server.subprocess.run",
                   return_value=mock_result) as mock_run:
            srv._run_manaosctl("status", "--verbose")

        cmd = mock_run.call_args[0][0]
        assert "status" in cmd
        assert "--verbose" in cmd


# ─────────────────────────────────────────────
# DashboardHandler — helper for testing
# ─────────────────────────────────────────────

def _make_handler(method: str = "GET", path: str = "/") -> srv.DashboardHandler:
    """テスト用ハンドラインスタンスを生成。"""
    handler = srv.DashboardHandler.__new__(srv.DashboardHandler)
    handler.path = path
    handler.command = method
    # wfile に書き込まれた内容をキャプチャ
    handler.wfile = BytesIO()
    handler._headers_sent: list = []  # type: ignore[valid-type]

    # HTTP レスポンスメソッドをモック
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    return handler


class TestDashboardHandlerSendJson:
    def test_sends_200_by_default(self):
        h = _make_handler()
        h._send_json({"key": "value"})
        h.send_response.assert_called_once_with(200)  # type: ignore

    def test_sends_custom_status(self):
        h = _make_handler()
        h._send_json({"error": "not found"}, status=404)
        h.send_response.assert_called_once_with(404)  # type: ignore

    def test_body_is_valid_json(self):
        h = _make_handler()
        h._send_json({"a": 1, "b": [2, 3]})
        body = h.wfile.getvalue().decode("utf-8")  # type: ignore
        assert json.loads(body) == {"a": 1, "b": [2, 3]}


class TestDashboardHandlerSendHtml:
    def test_sends_html_content_type(self):
        h = _make_handler()
        h._send_html("<h1>Hello</h1>")
        # send_header called with Content-Type html
        calls = [c[0] for c in h.send_header.call_args_list]  # type: ignore
        assert any("text/html" in str(v) for _, v in calls)

    def test_body_matches_input(self):
        h = _make_handler()
        h._send_html("<h1>Test</h1>", status=200)
        body = h.wfile.getvalue().decode("utf-8")  # type: ignore
        assert "<h1>Test</h1>" in body


class TestDashboardHandlerDoGet:
    def test_api_status_calls_manaosctl(self):
        h = _make_handler(path="/api/status")

        with patch("scripts.misc.manaos_dashboard_server._run_manaosctl",
                   return_value={"services": []}) as mock_run:
            h.do_GET()

        mock_run.assert_called_once_with("status")
        body = json.loads(h.wfile.getvalue().decode("utf-8"))  # type: ignore
        assert "services" in body

    def test_api_events_calls_read_events(self):
        h = _make_handler(path="/api/events")

        with patch.object(srv, "read_events", return_value=[{"id": 99}]):
            h.do_GET()

        body = json.loads(h.wfile.getvalue().decode("utf-8"))  # type: ignore
        assert body == [{"id": 99}]

    def test_api_summary_returns_empty_when_file_missing(self, tmp_path):
        h = _make_handler(path="/api/summary")

        with patch.object(srv, "SUMMARY_JSON", tmp_path / "nonexistent.json"):
            h.do_GET()

        body = json.loads(h.wfile.getvalue().decode("utf-8"))  # type: ignore
        assert body == {}

    def test_api_summary_returns_content_when_file_exists(self, tmp_path):
        summary = {"uptime": 3600}
        summary_file = tmp_path / "events.summary.json"
        summary_file.write_text(json.dumps(summary), encoding="utf-8")

        h = _make_handler(path="/api/summary")
        with patch.object(srv, "SUMMARY_JSON", summary_file):
            h.do_GET()

        body = json.loads(h.wfile.getvalue().decode("utf-8"))  # type: ignore
        assert body == summary

    def test_root_returns_html_or_404(self):
        h = _make_handler(path="/")
        h.do_GET()
        # Either HTML or 404 — just check no crash and something written
        assert h.wfile.getvalue()  # type: ignore

    def test_unknown_path_returns_404_json(self):
        h = _make_handler(path="/unknown/path")
        h.do_GET()
        body = json.loads(h.wfile.getvalue().decode("utf-8"))  # type: ignore
        assert "error" in body
        h.send_response.assert_called_with(404)  # type: ignore
