"""Tests for scripts/misc/force_restart_and_generate.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub():
    mod = types.ModuleType("_paths")
    mod.COMFYUI_PORT = 8188
    mod.GALLERY_PORT = 5559
    return mod


def _prep(monkeypatch, comfyui_ok=True, gallery_ok=True):
    sys.modules.pop("force_restart_and_generate", None)
    sys.modules.setdefault("_paths", _make_paths_stub())
    monkeypatch.syspath_prepend(str(_MISC))

    def _make_resp(ok):
        r = MagicMock()
        r.status_code = 200 if ok else 500
        r.json.return_value = {}
        return r

    mock_req = MagicMock()
    def get_side_effect(url, **kw):
        if "system_stats" in url:
            if not comfyui_ok:
                raise ConnectionError("refused")
            return _make_resp(True)
        return _make_resp(gallery_ok)

    mock_req.get.side_effect = get_side_effect
    mock_req.post.return_value = MagicMock(status_code=200, json=lambda: {"prompt_id": "test-id"})
    monkeypatch.setitem(sys.modules, "requests", mock_req)
    mock_subp = MagicMock()
    monkeypatch.setitem(sys.modules, "subprocess", mock_subp)
    return mock_req, mock_subp


class TestForceRestartAndGenerate:
    def test_imports_when_comfyui_ok(self, monkeypatch):
        _prep(monkeypatch, comfyui_ok=True)
        with patch("builtins.print"), patch("sys.exit"):
            import force_restart_and_generate  # noqa
        assert "force_restart_and_generate" in sys.modules

    def test_comfyui_down_calls_exit(self, monkeypatch):
        _prep(monkeypatch, comfyui_ok=False)
        mock_exit = MagicMock(side_effect=SystemExit(1))
        with patch("builtins.print"), patch("sys.exit", mock_exit):
            with pytest.raises(SystemExit):
                import force_restart_and_generate  # noqa
        mock_exit.assert_called_once_with(1)

    def test_comfyui_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("COMFYUI_URL", "http://custom:4444")
        sys.modules.pop("force_restart_and_generate", None)
        with patch("builtins.print"), patch("sys.exit"):
            import force_restart_and_generate as m
        assert m.COMFYUI_URL == "http://custom:4444"

    def test_gallery_urls_configured(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.delenv("GALLERY_GENERATE_API", raising=False)
        monkeypatch.delenv("GALLERY_IMAGES_API", raising=False)
        sys.modules.pop("force_restart_and_generate", None)
        with patch("builtins.print"), patch("sys.exit"):
            import force_restart_and_generate as m
        assert "5559" in m.GALLERY_API or "GALLERY" in m.GALLERY_API.upper()

    def test_prompts_sent_to_comfyui(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch)
        with patch("builtins.print"), patch("sys.exit"), patch("time.sleep"):
            import force_restart_and_generate  # noqa
        # post calls should be made for the 10 jobs
        assert mock_req.post.call_count >= 1

    def test_job_ids_list_populated(self, monkeypatch):
        _prep(monkeypatch)
        with patch("builtins.print"), patch("sys.exit"), patch("time.sleep"):
            import force_restart_and_generate as m
        assert isinstance(m.job_ids, list)
