"""Tests for scripts/misc/show_images.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _run(monkeypatch, images, count=None):
    sys.modules.pop("show_images", None)
    monkeypatch.syspath_prepend(str(_MISC))
    if count is None:
        count = len(images)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"images": images, "count": count}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)
    with patch("builtins.print"):
        import show_images
    return show_images, mock_req


def _make_image(i):
    return {
        "filename": f"img_{i}.png",
        "size": 1024 * i,
        "created_at": f"2024-01-{i:02d}T12:00:00",
    }


class TestShowImages:
    def test_imports(self, monkeypatch):
        _, _ = _run(monkeypatch, [_make_image(1)])
        assert "show_images" in sys.modules

    def test_requests_get_called(self, monkeypatch):
        _, mock_req = _run(monkeypatch, [_make_image(1)])
        mock_req.get.assert_called_once()
        url = mock_req.get.call_args[0][0]
        assert "5559" in url or "api/images" in url

    def test_with_multiple_images(self, monkeypatch):
        imgs = [_make_image(i) for i in range(1, 6)]
        show_images, mock_req = _run(monkeypatch, imgs, count=5)
        mock_req.get.assert_called_once()

    def test_with_more_than_10_images(self, monkeypatch):
        imgs = [_make_image(i) for i in range(1, 16)]
        show_images, mock_req = _run(monkeypatch, imgs, count=15)
        mock_req.get.assert_called_once()

    def test_json_called(self, monkeypatch):
        imgs = [_make_image(1)]
        _, mock_req = _run(monkeypatch, imgs)
        mock_req.get.return_value.json.assert_called()

    def test_error_handled(self, monkeypatch):
        sys.modules.pop("show_images", None)
        monkeypatch.syspath_prepend(str(_MISC))
        mock_req = MagicMock()
        mock_req.get.side_effect = Exception("connection refused")
        monkeypatch.setitem(sys.modules, "requests", mock_req)
        with patch("builtins.print"):
            import show_images  # should not raise
        assert True
