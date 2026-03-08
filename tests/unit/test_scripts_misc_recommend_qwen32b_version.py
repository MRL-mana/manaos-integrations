"""Tests for scripts/misc/recommend_qwen32b_version.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub(port=1234):
    mod = types.ModuleType("_paths")
    mod.LM_STUDIO_PORT = port
    return mod


def _prep(monkeypatch, request_ok=True):
    sys.modules.pop("recommend_qwen32b_version", None)
    sys.modules.pop("manaos_integrations._paths", None)
    monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
    monkeypatch.syspath_prepend(str(_MISC))

    mock_resp = MagicMock()
    mock_resp.status_code = 200 if request_ok else 500
    mock_resp.json.return_value = {"data": [{"id": "qwen2.5-coder-32b-instruct-q4_k_m"}]}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    with patch("builtins.print"):
        import recommend_qwen32b_version  # noqa
    return mock_req


class TestRecommendQwen32bVersion:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "recommend_qwen32b_version" in sys.modules

    def test_lm_studio_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("LM_STUDIO_URL", "http://custom:4321")
        sys.modules.pop("recommend_qwen32b_version", None)
        with patch("builtins.print"):
            import recommend_qwen32b_version as m
        assert m.DEFAULT_LM_STUDIO_URL == "http://custom:4321"

    def test_default_url_contains_port(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.delenv("LM_STUDIO_URL", raising=False)
        sys.modules.pop("recommend_qwen32b_version", None)
        with patch("builtins.print"):
            import recommend_qwen32b_version as m
        assert "1234" in m.DEFAULT_LM_STUDIO_URL

    def test_requests_get_called(self, monkeypatch):
        mock_req = _prep(monkeypatch)
        assert mock_req.get.called

    def test_prints_recommendations(self, monkeypatch):
        sys.modules.pop("recommend_qwen32b_version", None)
        sys.modules.setdefault("_paths", _make_paths_stub())
        monkeypatch.syspath_prepend(str(_MISC))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "qwen2.5-32b-q4"}]}
        mock_req = MagicMock()
        mock_req.get.return_value = mock_resp
        monkeypatch.setitem(sys.modules, "requests", mock_req)
        printed = []
        with patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import recommend_qwen32b_version  # noqa
        assert len(printed) > 0
