# -*- coding: utf-8 -*-
"""tests for scripts/misc/rows_integration.py"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.misc.rows_integration import RowsIntegration


def _make_ri(api_key: str = "test-key") -> RowsIntegration:
    return RowsIntegration(api_key=api_key)


def _make_session_response(status_code: int, json_data: Any):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Init / is_available
# ---------------------------------------------------------------------------
class TestInit:
    def test_with_explicit_key(self):
        ri = _make_ri("mykey")
        assert ri.api_key == "mykey"

    def test_no_key_from_env(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        assert ri.api_key is None

    def test_key_from_env(self, monkeypatch):
        monkeypatch.setenv("ROWS_API_KEY", "env-key")
        ri = RowsIntegration()
        assert ri.api_key == "env-key"

    def test_base_url_stored(self):
        ri = RowsIntegration(api_key="k", base_url="https://myrows.com/v2/")
        assert ri.base_url == "https://myrows.com/v2"

    def test_webhook_url_stored(self):
        ri = RowsIntegration(api_key="k", webhook_url="http://localhost/webhook")
        assert ri.webhook_url == "http://localhost/webhook"

    def test_session_created_with_key(self):
        ri = _make_ri()
        assert ri.session is not None

    def test_session_none_without_key(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        assert ri.session is None

    def test_last_error_none_initially(self):
        ri = _make_ri()
        assert ri.last_error is None


class TestIsAvailable:
    def test_with_key_and_session(self):
        assert _make_ri().is_available() is True

    def test_without_key(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        assert RowsIntegration().is_available() is False

    def test_empty_key(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration(api_key="")
        assert ri.is_available() is False


# ---------------------------------------------------------------------------
# _make_request (no session = returns None)
# ---------------------------------------------------------------------------
class TestMakeRequest:
    def test_no_session_returns_none(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        result = ri._make_request("GET", "/spreadsheets")
        assert result is None

    def test_no_session_sets_last_error(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        ri._make_request("GET", "/spreadsheets")
        assert ri.last_error is not None
        assert ri.last_error["type"] == "unavailable"

    def test_successful_get(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"id": "ss1"})
        result = ri._make_request("GET", "/spreadsheets/ss1")
        assert result == {"id": "ss1"}
        assert ri.last_error is None

    def test_404_returns_none(self):
        import requests as req
        ri = _make_ri()
        ri.session = MagicMock()
        resp = _make_session_response(404, {"message": "not found"})
        resp.raise_for_status.side_effect = req.exceptions.HTTPError(response=resp)
        ri.session.request.return_value = resp
        result = ri._make_request("GET", "/spreadsheets/notexist", max_retries=1)
        assert result is None

    def test_connection_error_returns_none(self):
        import requests as req
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.side_effect = req.exceptions.ConnectionError("fail")
        result = ri._make_request("GET", "/x", max_retries=1)
        assert result is None

    def test_timeout_returns_none(self):
        import requests as req
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.side_effect = req.exceptions.Timeout("timeout")
        result = ri._make_request("GET", "/x", max_retries=1)
        assert result is None
        assert ri.last_error["type"] == "timeout"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Spreadsheet CRUD methods
# ---------------------------------------------------------------------------
class TestGetSpreadsheet:
    def test_returns_data(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"id": "ss1", "title": "T"})
        result = ri.get_spreadsheet("ss1")
        assert result["id"] == "ss1"  # type: ignore[index]

    def test_no_session_returns_none(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        assert ri.get_spreadsheet("ss1") is None


class TestListSpreadsheets:
    def test_old_format(self):
        ri = _make_ri()
        ri.session = MagicMock()
        data = {"spreadsheets": [{"id": "ss1"}, {"id": "ss2"}]}
        ri.session.request.return_value = _make_session_response(200, data)
        result = ri.list_spreadsheets()
        assert len(result) == 2  # type: ignore
        assert result[0]["id"] == "ss1"  # type: ignore[index]

    def test_new_format_items(self):
        ri = _make_ri()
        ri.session = MagicMock()
        data = [{"items": [{"id": "a"}, {"id": "b"}], "next_page_results": None}]
        ri.session.request.return_value = _make_session_response(200, data)
        result = ri.list_spreadsheets()
        assert len(result) == 2  # type: ignore

    def test_dict_items_format(self):
        ri = _make_ri()
        ri.session = MagicMock()
        data = {"items": [{"id": "x"}]}
        ri.session.request.return_value = _make_session_response(200, data)
        result = ri.list_spreadsheets()
        assert result[0]["id"] == "x"  # type: ignore[index]

    def test_unexpected_format_sets_error(self):
        ri = _make_ri()
        ri.session = MagicMock()
        data = "unexpected string"
        ri.session.request.return_value = _make_session_response(200, data)
        result = ri.list_spreadsheets()
        assert result is None
        assert ri.last_error["type"] == "unexpected_response"  # type: ignore[index]


class TestCreateSpreadsheet:
    def test_sends_title(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"id": "new1"})
        result = ri.create_spreadsheet("My Sheet")
        assert result["id"] == "new1"  # type: ignore[index]
        called_kwargs = ri.session.request.call_args
        assert called_kwargs is not None


# ---------------------------------------------------------------------------
# Cell operations
# ---------------------------------------------------------------------------
class TestUpdateCell:
    def test_successful_update(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"updated": True})
        result = ri.update_cell("ss1", "Sheet1", "A1", "hello")
        assert result["updated"] is True  # type: ignore[index]

    def test_no_session_returns_none(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        assert ri.update_cell("ss1", "Sheet1", "A1", "v") is None


class TestGetCell:
    def test_successful_get(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"cell": "A1", "value": 42})
        result = ri.get_cell("ss1", "Sheet1", "A1")
        assert result["value"] == 42  # type: ignore[index]


class TestGetRange:
    def test_extracts_values(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"values": [[1, 2], [3, 4]]})
        result = ri.get_range("ss1", "Sheet1", "A1:B2")
        assert result == [[1, 2], [3, 4]]

    def test_no_values_key_returns_raw(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"other": "data"})
        result = ri.get_range("ss1", "Sheet1", "A1:B2")
        assert result == {"other": "data"}


class TestUpdateRange:
    def test_successful_update(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"ok": True})
        result = ri.update_range("ss1", "Sheet1", "A1:B2", [[1, 2], [3, 4]])
        assert result["ok"] is True  # type: ignore[index]


class TestSendToRows:
    def test_sends_data(self):
        ri = _make_ri()
        ri.session = MagicMock()
        # _get_last_row calls get_range -> _make_request; then batch_update -> _make_request
        # Provide row data for _get_last_row and success for batch_update
        ri.session.request.side_effect = [
            _make_session_response(200, {"values": [["h1", "h2"], ["v1", "v2"]]}),   # get_range call
            _make_session_response(200, {"updated_rows": 1}),                         # batch_update call
        ]
        result = ri.send_to_rows("ss1", {"h1": "val1", "h2": "val2"})
        assert result is not None


# ---------------------------------------------------------------------------
# AI methods
# ---------------------------------------------------------------------------
class TestAiQuery:
    def test_returns_result(self):
        ri = _make_ri()
        ri.session = MagicMock()
        ri.session.request.return_value = _make_session_response(200, {"answer": "result"})
        result = ri.ai_query("ss1", "売上を分析して")
        assert result["answer"] == "result"  # type: ignore[index]

    def test_no_session_returns_none(self, monkeypatch):
        monkeypatch.delenv("ROWS_API_KEY", raising=False)
        ri = RowsIntegration()
        assert ri.ai_query("ss1", "q") is None
