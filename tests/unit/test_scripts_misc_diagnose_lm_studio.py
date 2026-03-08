"""Tests for scripts/misc/diagnose_lm_studio.py"""
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


def _prep(monkeypatch, port=1234, server_ok=True):
    sys.modules.pop("diagnose_lm_studio", None)
    sys.modules.pop("manaos_integrations._paths", None)
    sys.modules.setdefault("_paths", _make_paths_stub(port))
    monkeypatch.syspath_prepend(str(_MISC))

    mock_resp = MagicMock()
    mock_resp.status_code = 200 if server_ok else 500
    mock_resp.json.return_value = {"data": [{"id": "qwen2.5"}, {"id": "gemma3"}]}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)
    return mock_req, mock_resp


class TestDiagnoseLmStudioImport:
    def test_imports_server_ok(self, monkeypatch):
        _prep(monkeypatch, server_ok=True)
        with patch("builtins.print"), patch("sys.exit"):
            import diagnose_lm_studio  # noqa
        assert "diagnose_lm_studio" in sys.modules

    def test_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("LM_STUDIO_URL", "http://custom:9999")
        sys.modules.pop("diagnose_lm_studio", None)
        with patch("builtins.print"), patch("sys.exit"):
            import diagnose_lm_studio as m
        assert m.DEFAULT_LM_STUDIO_URL == "http://custom:9999"

    def test_default_url_contains_port(self, monkeypatch):
        _prep(monkeypatch, port=1234)
        monkeypatch.delenv("LM_STUDIO_URL", raising=False)
        sys.modules.pop("diagnose_lm_studio", None)
        with patch("builtins.print"), patch("sys.exit"):
            import diagnose_lm_studio as m
        assert "1234" in m.DEFAULT_LM_STUDIO_URL

    def test_server_error_calls_sys_exit(self, monkeypatch):
        _prep(monkeypatch, server_ok=False)
        sys.modules.pop("diagnose_lm_studio", None)
        mock_exit = MagicMock(side_effect=SystemExit(1))
        with patch("builtins.print"), patch("sys.exit", mock_exit):
            with pytest.raises(SystemExit):
                import diagnose_lm_studio  # noqa
        mock_exit.assert_called_once_with(1)

    def test_connection_error_calls_sys_exit(self, monkeypatch):
        sys.modules.pop("diagnose_lm_studio", None)
        sys.modules.setdefault("_paths", _make_paths_stub())
        monkeypatch.syspath_prepend(str(_MISC))
        mock_req = MagicMock()
        mock_req.get.side_effect = ConnectionError("refused")
        monkeypatch.setitem(sys.modules, "requests", mock_req)
        mock_exit = MagicMock(side_effect=SystemExit(1))
        with patch("builtins.print"), patch("sys.exit", mock_exit):
            with pytest.raises(SystemExit):
                import diagnose_lm_studio  # noqa

    def test_requests_called_with_models_endpoint(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch)
        with patch("builtins.print"), patch("sys.exit"):
            import diagnose_lm_studio  # noqa
        called_urls = [call.args[0] for call in mock_req.get.call_args_list if call.args]
        assert any("/v1/models" in u for u in called_urls)
