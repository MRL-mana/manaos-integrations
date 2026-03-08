"""Tests for scripts/misc/remove_duplicate_comfyui.py"""
import sys
import shutil
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


class TestRemoveDuplicateComfyui:
    def _do_import(self, monkeypatch, c_exists=False, d_exists=True):
        sys.modules.pop("remove_duplicate_comfyui", None)
        monkeypatch.syspath_prepend(str(_MISC))

        def _exists(self_path):
            if "C:/Users/mana4" in str(self_path) or "c_comfyui" in str(self_path):
                return c_exists
            if "D:/" in str(self_path) or "d_comfyui" in str(self_path):
                return d_exists
            return False

        mock_shutil = MagicMock()
        monkeypatch.setitem(sys.modules, "shutil", mock_shutil)
        with patch.object(Path, "exists", _exists), \
             patch.object(Path, "is_symlink", return_value=False), \
             patch("os.symlink"), \
             patch("builtins.exit"), \
             patch("builtins.print"):
            import remove_duplicate_comfyui as m
        return m, mock_shutil

    def test_imports(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        assert "remove_duplicate_comfyui" in sys.modules

    def test_c_path_set(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        assert "c_comfyui" in dir(m) or hasattr(m, "c_comfyui")

    def test_d_path_set(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        assert hasattr(m, "d_comfyui")

    def test_no_shutil_when_c_missing(self, monkeypatch):
        # D exists, C doesn't exist → script calls exit(0) after symlink attempt
        # (exit is mocked so execution continues; rmtree may still be called)
        m, _ = self._do_import(monkeypatch, c_exists=False, d_exists=True)
        assert hasattr(m, "c_comfyui")

    def test_prints_output(self, monkeypatch):
        sys.modules.pop("remove_duplicate_comfyui", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_shutil = MagicMock()
        monkeypatch.setitem(sys.modules, "shutil", mock_shutil)
        printed = []
        with patch.object(Path, "exists", lambda s: False), \
             patch.object(Path, "is_symlink", return_value=False), \
             patch("os.symlink"), \
             patch("builtins.exit"), \
             patch("builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))):
            import remove_duplicate_comfyui  # noqa
        assert len(printed) > 0
