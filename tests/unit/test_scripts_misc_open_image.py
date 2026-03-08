"""Tests for scripts/misc/open_image.py"""
import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


class TestOpenImage:
    def _do_import(self, monkeypatch, image_exists=False, alt_exists=False):
        sys.modules.pop("open_image", None)
        monkeypatch.syspath_prepend(str(_MISC))

        def path_exists(self_path):
            if "generated_images" in str(self_path) and str(self_path).endswith(".png"):
                return image_exists
            if str(self_path).endswith("generated_images"):
                return alt_exists
            return False

        with patch.object(Path, "exists", path_exists), \
             patch("os.startfile", MagicMock()) as mock_startfile, \
             patch("builtins.print"):
            import open_image as m
        return m

    def test_imports(self, monkeypatch):
        self._do_import(monkeypatch)
        assert "open_image" in sys.modules

    def test_startfile_called_when_image_exists(self, monkeypatch):
        sys.modules.pop("open_image", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_sf = MagicMock()
        with patch.object(Path, "exists", lambda s: True), \
             patch("os.startfile", mock_sf), \
             patch("builtins.print"):
            import open_image  # noqa
        mock_sf.assert_called_once()

    def test_startfile_not_called_when_image_missing_and_dir_missing(self, monkeypatch):
        sys.modules.pop("open_image", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_sf = MagicMock()
        with patch.object(Path, "exists", lambda s: False), \
             patch("os.startfile", mock_sf), \
             patch("builtins.print"):
            import open_image  # noqa
        mock_sf.assert_not_called()

    def test_prints_something(self, monkeypatch):
        sys.modules.pop("open_image", None)
        monkeypatch.syspath_prepend(str(_MISC))
        printed = []
        with patch.object(Path, "exists", lambda s: False), \
             patch("os.startfile", MagicMock()), \
             patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import open_image  # noqa
        assert len(printed) > 0
