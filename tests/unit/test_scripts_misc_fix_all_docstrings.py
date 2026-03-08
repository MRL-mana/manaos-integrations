"""Tests for scripts/misc/fix_all_docstrings.py"""
import sys
from unittest.mock import MagicMock, patch, mock_open
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"

_FAKE_LINES = ["line 0\n"] * 1700  # enough lines for index 1670


def _prep(monkeypatch, fake_lines=None):
    sys.modules.pop("fix_all_docstrings", None)
    monkeypatch.syspath_prepend(str(_MISC))
    lines = fake_lines if fake_lines is not None else list(_FAKE_LINES)

    m_open = mock_open(read_data="".join(lines))
    # mock_open doesn't handle readlines() well; patch separately
    handle = MagicMock()
    handle.__enter__ = MagicMock(return_value=handle)
    handle.__exit__ = MagicMock(return_value=False)
    handle.readlines.return_value = lines
    handle.writelines = MagicMock()
    mock_open_factory = MagicMock(return_value=handle)

    with patch("builtins.open", mock_open_factory), patch("builtins.print"):
        import fix_all_docstrings  # noqa
    return mock_open_factory, handle


class TestFixAllDocstrings:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "fix_all_docstrings" in sys.modules

    def test_opens_target_file_for_read(self, monkeypatch):
        mock_open_factory, _ = _prep(monkeypatch)
        read_calls = [c for c in mock_open_factory.call_args_list if c.args and "create_system3_status.py" in c.args[0]]
        assert len(read_calls) >= 1

    def test_writes_back_to_file(self, monkeypatch):
        _, handle = _prep(monkeypatch)
        handle.writelines.assert_called_once()

    def test_fixes_dict_has_line_1550(self, monkeypatch):
        """fixes辞書のキー1550が存在する"""
        mock_factory, handle = _prep(monkeypatch)
        # The module applies fixes dict; writelines was called with modified lines
        written = handle.writelines.call_args[0][0]
        assert written[1550] == '    """直近の改善件数をカウント"""\n'

    def test_fixes_dict_has_line_1670(self, monkeypatch):
        """fixes辞書のキー1670が存在する"""
        _, handle = _prep(monkeypatch)
        written = handle.writelines.call_args[0][0]
        assert written[1670] == '    """System3_Status.mdの内容を生成"""\n'

    def test_prints_completion_message(self, monkeypatch):
        sys.modules.pop("fix_all_docstrings", None)
        monkeypatch.syspath_prepend(str(_MISC))
        lines = list(_FAKE_LINES)
        handle = MagicMock()
        handle.__enter__ = MagicMock(return_value=handle)
        handle.__exit__ = MagicMock(return_value=False)
        handle.readlines.return_value = lines
        handle.writelines = MagicMock()
        printed = []
        with patch("builtins.open", MagicMock(return_value=handle)), \
             patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import fix_all_docstrings  # noqa
        assert any("fixed" in p.lower() or "fix" in p.lower() for p in printed)
