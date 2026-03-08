"""tests/unit/test_scripts_misc_rows_example_log_management.py

rows_example_log_management.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.rows_example_log_management as _mod


class TestGenerateSampleLogs:
    def test_default_count(self):
        logs = _mod.generate_sample_logs()
        assert len(logs) == 50

    def test_custom_count(self):
        logs = _mod.generate_sample_logs(10)
        assert len(logs) == 10

    def test_zero_count(self):
        logs = _mod.generate_sample_logs(0)
        assert logs == []

    def test_log_structure(self):
        logs = _mod.generate_sample_logs(3)
        for log in logs:
            assert "日時" in log
            assert "レベル" in log
            assert "サービス" in log
            assert "メッセージ" in log

    def test_log_level_valid(self):
        valid_levels = {"INFO", "WARNING", "ERROR", "DEBUG"}
        logs = _mod.generate_sample_logs(20)
        for log in logs:
            assert log["レベル"] in valid_levels

    def test_returns_list(self):
        result = _mod.generate_sample_logs(5)
        assert isinstance(result, list)


class TestCreateLogSpreadsheet:
    def test_success_returns_id(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"spreadsheet": {"id": "sheet-abc"}}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_log_spreadsheet()
        assert result == "sheet-abc"

    def test_failure_returns_none(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.create_log_spreadsheet()
        assert result is None


class TestSendLogData:
    def test_success_returns_true(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"added_rows": 5}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        logs = _mod.generate_sample_logs(5)
        result = _mod.send_log_data("sheet-abc", logs)
        assert result is True

    def test_failure_returns_false(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        logs = _mod.generate_sample_logs(2)
        result = _mod.send_log_data("sheet-abc", logs)
        assert result is False
