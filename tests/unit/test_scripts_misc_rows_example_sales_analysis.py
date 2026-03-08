"""tests/unit/test_scripts_misc_rows_example_sales_analysis.py

rows_example_sales_analysis.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.rows_example_sales_analysis as _mod


class TestCreateSalesSpreadsheet:
    def test_success_returns_id(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"spreadsheet": {"id": "sales-123"}}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_sales_spreadsheet()
        assert result == "sales-123"

    def test_failure_returns_none(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_sales_spreadsheet()
        assert result is None


class TestSendSalesData:
    def test_success_returns_true(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"added_rows": 30}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.send_sales_data("sales-123")
        assert result is True

    def test_failure_returns_false(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.send_sales_data("sales-123")
        assert result is False


class TestAnalyzeSalesTrend:
    def test_success_returns_result(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"summary": "trend up"}}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_sales_trend("sales-123")
        assert result is not None

    def test_failure_returns_none(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_sales_trend("sales-123")
        assert result is None
