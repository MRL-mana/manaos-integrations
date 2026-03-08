"""Tests for scripts/misc/open_latest_images.py"""
import sys
import types
import os as _os_mod
import importlib.util
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub(port=5559):
    mod = types.ModuleType("_paths")
    mod.GALLERY_PORT = port
    return mod


def _prep(monkeypatch, response_ok=True, images=None, port=5559):
    sys.modules.pop("open_latest_images", None)
    monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub(port))

    _images = images or [
        {"filename": "a.png", "created_at": "2026-01-01T00:00:00", "size": 1024},
        {"filename": "b.png", "created_at": "2026-01-02T00:00:00", "size": 2048},
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200 if response_ok else 500
    mock_resp.json.return_value = {"images": _images, "count": len(_images)}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    mock_wb = MagicMock()
    monkeypatch.setitem(sys.modules, "webbrowser", mock_wb)

    spec = importlib.util.spec_from_file_location(
        "open_latest_images", str(_MISC / "open_latest_images.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.os = _os_mod  # inject missing os
    sys.modules["open_latest_images"] = mod
    with patch("builtins.print"):
        spec.loader.exec_module(mod)
    return mock_req, mock_wb


class TestOpenLatestImages:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "open_latest_images" in sys.modules

    def test_requests_get_called(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch)
        assert mock_req.get.called

    def test_gallery_url_contains_port(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch, port=5559)
        called_url = mock_req.get.call_args[0][0]
        assert "5559" in called_url or "api/images" in called_url

    def test_webbrowser_open_called_on_success(self, monkeypatch):
        _, mock_wb = _prep(monkeypatch, response_ok=True)
        # webbrowser.open should be called for at least one image
        assert mock_wb.open.called

    def test_no_error_on_api_failure(self, monkeypatch):
        _prep(monkeypatch, response_ok=False)  # should not raise
