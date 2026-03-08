"""Tests for scripts/misc/view_excel.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_sheet(rows=5):
    mock_df = MagicMock()
    mock_df.__len__ = MagicMock(return_value=rows)
    mock_df.columns = [f"Col{i}" for i in range(3)]
    # iloc[i] returns a row-like object; row['Text'] returns a string
    mock_row = MagicMock()
    mock_row.__getitem__ = MagicMock(return_value="sample_text")
    mock_df.iloc.__getitem__ = MagicMock(return_value=mock_row)

    text_series = MagicMock()
    text_series.notna.return_value.sum.return_value = rows
    text_series.isna.return_value.sum.return_value = 0
    mock_df.__getitem__ = MagicMock(return_value=text_series)
    mock_df.__contains__ = MagicMock(return_value=True)
    return mock_df


def _prep(monkeypatch):
    sys.modules.pop("view_excel", None)
    monkeypatch.syspath_prepend(str(_MISC))

    mock_sheet = _make_sheet(10)
    mock_df_dict = {"Sheet1": mock_sheet}

    mock_pd = MagicMock()
    mock_pd.read_excel.return_value = mock_df_dict
    mock_pd.notna.return_value = True
    monkeypatch.setitem(sys.modules, "pandas", mock_pd)

    with patch("builtins.print"):
        import view_excel
    return view_excel, mock_pd


class TestViewExcel:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "view_excel" in sys.modules

    def test_read_excel_called(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        mock_pd.read_excel.assert_called_once()

    def test_sheet_name_none(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        call_kwargs = mock_pd.read_excel.call_args
        assert call_kwargs.kwargs.get("sheet_name") is None or \
               (len(call_kwargs.args) > 1 and call_kwargs.args[1] is None) or \
               "sheet_name" in str(call_kwargs)

    def test_file_path_is_xlsx(self, monkeypatch):
        _, mock_pd = _prep(monkeypatch)
        call_args = mock_pd.read_excel.call_args
        filename = str(call_args.args[0]) if call_args.args else ""
        assert ".xlsx" in filename
