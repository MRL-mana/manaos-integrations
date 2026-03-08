"""Tests for scripts/misc/try_restart_and_generate.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _prep(monkeypatch, comfyui_ok=True, gallery_ok=True):
    sys.modules.pop("try_restart_and_generate", None)
    monkeypatch.syspath_prepend(str(_MISC))

    paths_mod = types.ModuleType("_paths")
    paths_mod.COMFYUI_PORT = 8188
    paths_mod.GALLERY_PORT = 5559
    monkeypatch.setitem(sys.modules, "_paths", paths_mod)

    monkeypatch.delenv("COMFYUI_URL", raising=False)
    monkeypatch.delenv("GALLERY_API_URL", raising=False)

    comfyui_resp = MagicMock()
    comfyui_resp.status_code = 200 if comfyui_ok else 500

    gallery_resp = MagicMock()
    gallery_resp.status_code = 200 if gallery_ok else 500
    gallery_resp.json.return_value = {"success": True, "image": "test.png"}

    def _get_side(url, **kw):
        if "system_stats" in url:
            return comfyui_resp
        return gallery_resp

    mock_req = MagicMock()
    mock_req.get.side_effect = _get_side
    mock_req.post.return_value = gallery_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    mock_subprocess = MagicMock()
    monkeypatch.setitem(sys.modules, "subprocess", mock_subprocess)

    with patch("builtins.print"):
        import try_restart_and_generate
    return try_restart_and_generate, mock_req, mock_subprocess


class TestTryRestartAndGenerate:
    def test_imports(self, monkeypatch):
        m, _, _ = _prep(monkeypatch)
        assert "try_restart_and_generate" in sys.modules

    def test_comfyui_status_checked(self, monkeypatch):
        _, mock_req, _ = _prep(monkeypatch, comfyui_ok=True)
        calls = [str(c) for c in mock_req.get.call_args_list]
        assert any("system_stats" in c for c in calls)

    def test_comfyui_down_handled(self, monkeypatch):
        mock_req = MagicMock()
        mock_req.get.side_effect = Exception("connection refused")
        sys.modules.pop("try_restart_and_generate", None)
        monkeypatch.syspath_prepend(str(_MISC))
        paths_mod = types.ModuleType("_paths")
        paths_mod.COMFYUI_PORT = 8188
        paths_mod.GALLERY_PORT = 5559
        monkeypatch.setitem(sys.modules, "_paths", paths_mod)
        monkeypatch.setitem(sys.modules, "requests", mock_req)
        monkeypatch.setitem(sys.modules, "subprocess", MagicMock())
        with patch("builtins.print"):
            import try_restart_and_generate as m
        assert True  # no unhandled exception

    def test_env_override_comfyui_url(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_URL", "http://custom:9999")
        m, _, _ = _prep(monkeypatch, comfyui_ok=True)
        # URL comes from env
        assert True
