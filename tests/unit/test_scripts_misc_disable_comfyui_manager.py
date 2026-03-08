"""Tests for scripts/misc/disable_comfyui_manager.py"""
import sys
import types
from unittest.mock import MagicMock, patch, call
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


class TestDisableComfyuiManager:
    def _do_import(self, monkeypatch, comfyui_path=None, manager_exists=True, backup_exists=False, tmp_path=None):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        if comfyui_path:
            monkeypatch.setenv("COMFYUI_PATH", str(comfyui_path))
        else:
            monkeypatch.delenv("COMFYUI_PATH", raising=False)

        # Patch Path.exists and Path.rename at instance level
        with patch("builtins.print"):
            import disable_comfyui_manager as m
        return m

    def test_imports(self, monkeypatch, tmp_path):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        monkeypatch.delenv("COMFYUI_PATH", raising=False)
        comfyui = tmp_path / "ComfyUI"
        comfyui.mkdir()
        manager_path = comfyui / "custom_nodes" / "ComfyUI-Manager"
        manager_path.mkdir(parents=True)
        monkeypatch.setenv("COMFYUI_PATH", str(comfyui))
        with patch("builtins.print"):
            import disable_comfyui_manager  # noqa
        assert "disable_comfyui_manager" in sys.modules

    def test_manager_path_uses_env(self, monkeypatch, tmp_path):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        custom_path = str(tmp_path)
        monkeypatch.setenv("COMFYUI_PATH", custom_path)
        with patch("builtins.print"):
            import disable_comfyui_manager as m
        assert str(tmp_path) in str(m.comfyui_path)

    def test_manager_not_present_no_rename(self, monkeypatch, tmp_path):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        monkeypatch.setenv("COMFYUI_PATH", str(tmp_path))
        printed = []
        with patch("builtins.print", side_effect=lambda *a, **k: printed.append(" ".join(str(x) for x in a))):
            import disable_comfyui_manager  # noqa
        assert not any("無効化中" in p for p in printed)

    def test_already_disabled_message(self, monkeypatch, tmp_path):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        comfyui = tmp_path / "ComfyUI"
        nodes = comfyui / "custom_nodes"
        nodes.mkdir(parents=True)
        (nodes / "ComfyUI-Manager").mkdir()
        (nodes / "ComfyUI-Manager.disabled").mkdir()
        monkeypatch.setenv("COMFYUI_PATH", str(comfyui))
        printed = []
        with patch("builtins.print", side_effect=lambda *a, **k: printed.append(" ".join(str(x) for x in a))):
            import disable_comfyui_manager  # noqa
        assert any("既に無効化" in p for p in printed)

    def test_disable_renames_directory(self, monkeypatch, tmp_path):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        comfyui = tmp_path / "ComfyUI"
        nodes = comfyui / "custom_nodes"
        nodes.mkdir(parents=True)
        (nodes / "ComfyUI-Manager").mkdir()
        monkeypatch.setenv("COMFYUI_PATH", str(comfyui))
        with patch("builtins.print"):
            import disable_comfyui_manager  # noqa
        assert (nodes / "ComfyUI-Manager.disabled").exists()
        assert not (nodes / "ComfyUI-Manager").exists()

    def test_default_comfyui_path(self, monkeypatch):
        sys.modules.pop("disable_comfyui_manager", None)
        monkeypatch.syspath_prepend(str(_MISC))
        monkeypatch.delenv("COMFYUI_PATH", raising=False)
        with patch("builtins.print"):
            import disable_comfyui_manager as m
        assert "ComfyUI" in str(m.comfyui_path)
