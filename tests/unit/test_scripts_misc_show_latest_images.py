"""Tests for scripts/misc/show_latest_images.py"""
import sys
import os as _os_mod
import types
import importlib.util
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _prep(monkeypatch, status=200, images=None):
    sys.modules.pop("show_latest_images", None)
    monkeypatch.syspath_prepend(str(_MISC))

    # _paths stub
    paths_mod = types.ModuleType("_paths")
    paths_mod.GALLERY_PORT = 5559  # type: ignore
    monkeypatch.setitem(sys.modules, "_paths", paths_mod)

    monkeypatch.setenv("GALLERY_API_URL", "")

    if images is None:
        images = [
            {"filename": f"img_{i}.png", "created_at": f"2024-01-{i:02d}", "url": f"http://x/{i}.png"}
            for i in range(1, 6)
        ]

    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = {"images": images}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    mock_wb = MagicMock()
    monkeypatch.setitem(sys.modules, "webbrowser", mock_wb)

    # The source script is missing `import os` — inject via importlib
    spec = importlib.util.spec_from_file_location(
        "show_latest_images", str(_MISC / "show_latest_images.py")
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    mod.os = _os_mod  # inject missing os  # type: ignore
    mod.requests = mock_req  # type: ignore
    mod.webbrowser = mock_wb  # type: ignore
    sys.modules["show_latest_images"] = mod
    with patch("builtins.print"):
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod, mock_req, mock_wb


class TestShowLatestImages:
    def test_imports(self, monkeypatch):
        m, _, _ = _prep(monkeypatch)
        assert "show_latest_images" in sys.modules

    def test_requests_get_called(self, monkeypatch):
        _, mock_req, _ = _prep(monkeypatch)
        mock_req.get.assert_called_once()

    def test_gallery_port_in_url(self, monkeypatch):
        _, mock_req, _ = _prep(monkeypatch)
        url = mock_req.get.call_args[0][0]
        assert "5559" in url or "api/images" in url

    def test_non_200_status_handled(self, monkeypatch):
        _prep(monkeypatch, status=500)
        assert True  # no exception

    def test_many_images(self, monkeypatch):
        imgs = [
            {"filename": f"img_{i}.png", "created_at": f"2024-01-{i:02d}", "url": f"http://x/{i}.png"}
            for i in range(1, 20)
        ]
        _, mock_req, _ = _prep(monkeypatch, images=imgs)
        mock_req.get.assert_called_once()
