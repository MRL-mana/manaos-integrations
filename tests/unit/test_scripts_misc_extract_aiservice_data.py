"""Tests for scripts/misc/extract_aiservice_data.py"""
import sys
import types
import json
import sqlite3
from unittest.mock import MagicMock, patch, call
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


_SAMPLE_DATA = json.dumps([
    {"id": "gen_1", "model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
    {"id": "gen_2", "model": "claude-3", "messages": [{"role": "user", "content": "hello"}]},
])


def _prep(monkeypatch, db_value=None):
    sys.modules.pop("extract_aiservice_data", None)
    monkeypatch.syspath_prepend(str(_MISC))

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    if db_value is None:
        mock_cursor.fetchone.return_value = (_SAMPLE_DATA,)
    else:
        mock_cursor.fetchone.return_value = db_value

    with patch("sqlite3.connect", return_value=mock_conn), \
         patch("builtins.print"):
        import extract_aiservice_data  # noqa
    return mock_conn, mock_cursor


class TestExtractAiServiceDataImport:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "extract_aiservice_data" in sys.modules

    def test_sqlite_connect_called(self, monkeypatch):
        mock_conn, mock_cursor = _prep(monkeypatch)
        mock_conn.cursor.assert_called()

    def test_query_for_aiservice_generations(self, monkeypatch):
        mock_conn, mock_cursor = _prep(monkeypatch)
        calls = [c.args[0] for c in mock_cursor.execute.call_args_list if c.args]
        assert any("aiService.generations" in q for q in calls)

    def test_no_data_case(self, monkeypatch):
        sys.modules.pop("extract_aiservice_data", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        with patch("sqlite3.connect", return_value=mock_conn), \
             patch("builtins.print"):
            import extract_aiservice_data  # noqa – should not raise

    def test_bytes_data_decoded(self, monkeypatch):
        sys.modules.pop("extract_aiservice_data", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (_SAMPLE_DATA.encode("utf-8"),)
        with patch("sqlite3.connect", return_value=mock_conn), \
             patch("builtins.print"):
            import extract_aiservice_data  # noqa – bytes path

    def test_db_path_uses_appdata(self, monkeypatch):
        mock_conn, mock_cursor = _prep(monkeypatch)
        # db_path is built from APPDATA at module level
        import extract_aiservice_data as m
        assert hasattr(m, "db_path")
