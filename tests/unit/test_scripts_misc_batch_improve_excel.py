"""Tests for scripts/misc/batch_improve_excel.py"""
import sys
import types
from unittest.mock import MagicMock, patch, call
import pytest


def _prep(monkeypatch):
    sys.modules.pop("batch_improve_excel", None)
    # stub improve_existing_excel
    _iem = types.ModuleType("improve_existing_excel")
    _iem.improve_excel_file = MagicMock(return_value=None)  # type: ignore
    monkeypatch.setitem(sys.modules, "improve_existing_excel", _iem)
    monkeypatch.syspath_prepend(
        str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts" / "misc")
    )
    return _iem


class TestBatchImproveExcelImport:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        import batch_improve_excel  # noqa
        assert "batch_improve_excel" in sys.modules

    def test_has_batch_improve(self, monkeypatch):
        _prep(monkeypatch)
        import batch_improve_excel as m
        assert callable(m.batch_improve)


class TestBatchImprove:
    def _setup(self, monkeypatch):
        iem = _prep(monkeypatch)
        import batch_improve_excel as m
        return m, iem

    def test_file_not_found_returns_early(self, monkeypatch, tmp_path):
        m, iem = self._setup(monkeypatch)
        with patch("os.path.exists", return_value=False), patch("builtins.print"):
            m.batch_improve()
        iem.improve_excel_file.assert_not_called()

    def test_file_found_calls_improve(self, monkeypatch, tmp_path):
        m, iem = self._setup(monkeypatch)
        mock_drive = MagicMock()
        mock_drive.upload_file.return_value = "file123"
        mock_gd = types.ModuleType("google_drive_integration")
        mock_gd.GoogleDriveIntegration = MagicMock(return_value=mock_drive)  # type: ignore
        monkeypatch.setitem(sys.modules, "google_drive_integration", mock_gd)

        mock_sheets = types.ModuleType("excel_to_google_sheets")
        mock_sheets.excel_to_google_sheets = MagicMock(return_value="http://sheets/url")  # type: ignore
        monkeypatch.setitem(sys.modules, "excel_to_google_sheets", mock_sheets)

        with patch("os.path.exists", return_value=True), patch("builtins.print"):
            m.batch_improve()
        iem.improve_excel_file.assert_called_once()

    def test_drive_upload_failure_handled(self, monkeypatch):
        m, iem = self._setup(monkeypatch)
        mock_drive = MagicMock()
        mock_drive.upload_file.return_value = None
        mock_gd = types.ModuleType("google_drive_integration")
        mock_gd.GoogleDriveIntegration = MagicMock(return_value=mock_drive)  # type: ignore
        monkeypatch.setitem(sys.modules, "google_drive_integration", mock_gd)

        mock_sheets = types.ModuleType("excel_to_google_sheets")
        mock_sheets.excel_to_google_sheets = MagicMock(return_value=None)  # type: ignore
        monkeypatch.setitem(sys.modules, "excel_to_google_sheets", mock_sheets)

        with patch("os.path.exists", return_value=True), patch("builtins.print"):
            m.batch_improve()  # should not raise
        mock_drive.upload_file.assert_called_once()

    def test_drive_exception_handled(self, monkeypatch):
        m, iem = self._setup(monkeypatch)
        mock_gd = types.ModuleType("google_drive_integration")
        mock_gd.GoogleDriveIntegration = MagicMock(side_effect=Exception("drive error"))  # type: ignore
        monkeypatch.setitem(sys.modules, "google_drive_integration", mock_gd)

        mock_sheets = types.ModuleType("excel_to_google_sheets")
        mock_sheets.excel_to_google_sheets = MagicMock(return_value=None)  # type: ignore
        monkeypatch.setitem(sys.modules, "excel_to_google_sheets", mock_sheets)

        with patch("os.path.exists", return_value=True), patch("builtins.print"):
            m.batch_improve()  # exception should be printed, not raised
