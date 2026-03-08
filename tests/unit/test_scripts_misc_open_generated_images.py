"""Tests for scripts/misc/open_generated_images.py"""
import sys
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


class TestOpenGeneratedImages:
    def _do_import(self, monkeypatch, files_exist=False):
        sys.modules.pop("open_generated_images", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_subp = MagicMock()
        monkeypatch.setitem(sys.modules, "subprocess", mock_subp)
        with patch("pathlib.Path.exists", return_value=files_exist), \
             patch("builtins.print"):
            import open_generated_images as m
        return m, mock_subp

    def test_imports(self, monkeypatch):
        m, _ = self._do_import(monkeypatch, files_exist=False)
        assert "open_generated_images" in sys.modules

    def test_comfyui_output_dir_set(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        assert "ComfyUI" in str(m.COMFYUI_OUTPUT_DIR)

    def test_generated_files_list_non_empty(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        assert len(m.generated_files) > 0

    def test_all_filenames_are_png(self, monkeypatch):
        m, _ = self._do_import(monkeypatch)
        for f in m.generated_files:
            assert f.endswith(".png")

    def test_no_subprocess_call_when_no_files(self, monkeypatch):
        _, mock_subp = self._do_import(monkeypatch, files_exist=False)
        assert not mock_subp.Popen.called

    def test_subprocess_called_when_files_exist(self, monkeypatch):
        sys.modules.pop("open_generated_images", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_subp = MagicMock()
        monkeypatch.setitem(sys.modules, "subprocess", mock_subp)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.print"):
            import open_generated_images  # noqa
        # subprocess.Popen should be called for up to 5 files
        assert mock_subp.Popen.called
