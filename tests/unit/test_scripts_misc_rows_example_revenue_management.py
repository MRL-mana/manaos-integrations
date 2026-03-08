"""tests/unit/test_scripts_misc_rows_example_revenue_management.py

rows_example_revenue_management.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.rows_example_revenue_management as _mod


class TestCreateRevenueSpreadsheet:
    def test_success_returns_id(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"spreadsheet": {"id": "rev-456"}}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_revenue_spreadsheet()
        assert result == "rev-456"

    def test_failure_returns_none(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_revenue_spreadsheet()
        assert result is None


class TestSendRevenueData:
    def test_success_returns_true(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"added_rows": 60}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.send_revenue_data("rev-456")
        assert result is True

    def test_failure_returns_false(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.send_revenue_data("rev-456")
        assert result is False


class TestAnalyzeRevenueTrends:
    def test_success_returns_list(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"summary": "growth"}}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_revenue_trends("rev-456")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_failure_returns_empty_list(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_revenue_trends("rev-456")
        assert isinstance(result, list)
        assert len(result) == 0
