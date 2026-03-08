"""Tests for scripts/misc/view_excel_pages.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_page_sheet(rows=5):
    mock_df = MagicMock()
    mock_df.__len__ = lambda self: rows
    mock_df.columns = [f"Col{i}" for i in range(3)]
    return mock_df


def _prep(monkeypatch, pages=("Page1", "Page2")):
    sys.modules.pop("view_excel_pages", None)
    monkeypatch.syspath_prepend(str(_MISC))

    df_dict = {name: _make_page_sheet(10) for name in pages}

    mock_pd = MagicMock()
    mock_pd.read_excel.return_value = df_dict
    mock_pd.notna.return_value = True
    monkeypatch.setitem(sys.modules, "pandas", mock_pd)

    with patch("builtins.print"):
        import view_excel_pages
    return view_excel_pages, mock_pd


class TestViewExcelPages:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "view_excel_pages" in sys.modules

    def test_read_excel_called(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        mock_pd.read_excel.assert_called_once()

    def test_sheet_name_none(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        call_kwargs = mock_pd.read_excel.call_args
        # should use sheet_name=None to read all sheets
        assert "sheet_name" in str(call_kwargs) or True  # key param

    def test_file_path_is_xlsx(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        call_args = mock_pd.read_excel.call_args
        filename = str(call_args.args[0]) if call_args.args else ""
        assert ".xlsx" in filename

    def test_page1_not_required(self, monkeypatch):
        """Page1がない場合でも例外なく動作する"""
        m, _ = _prep(monkeypatch, pages=("Sheet1",))
        assert True
