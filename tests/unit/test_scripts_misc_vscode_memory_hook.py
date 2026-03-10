"""Tests for scripts/misc/vscode_memory_hook.py"""
import sys
import types
import json
from unittest.mock import MagicMock, patch
from io import BytesIO
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _load(monkeypatch):
    sys.modules.pop("vscode_memory_hook", None)
    monkeypatch.syspath_prepend(str(_MISC))

    mock_mem_instance = MagicMock()
    mock_mem_instance.search_memories.return_value = [{"text": "memo", "score": 0.9}]
    mock_mem_instance.add_memory.return_value = None

    mem0_mod = types.ModuleType("mem0_integration")
    mem0_mod.Mem0Integration = MagicMock(return_value=mock_mem_instance)  # type: ignore
    monkeypatch.setitem(sys.modules, "mem0_integration", mem0_mod)

    with patch("builtins.print"):
        import vscode_memory_hook as m
    return m, mock_mem_instance


class TestVscodeMemoryHook:
    def test_module_loads(self, monkeypatch):
        m, _ = _load(monkeypatch)
        assert "vscode_memory_hook" in sys.modules

    def test_handler_class_exists(self, monkeypatch):
        m, _ = _load(monkeypatch)
        assert hasattr(m, "Handler")

    def test_port_default(self, monkeypatch):
        m, _ = _load(monkeypatch)
        assert m.PORT == 5210

    def test_port_from_env(self, monkeypatch):
        monkeypatch.setenv("MANAOS_VSCODE_HOOK_PORT", "5999")
        m, _ = _load(monkeypatch)
        assert m.PORT == 5999

    def test_mem_instance_created(self, monkeypatch):
        m, mock_mem = _load(monkeypatch)
        assert m.mem is mock_mem

    def test_handler_get_search(self, monkeypatch):
        m, mock_mem = _load(monkeypatch)
        handler = object.__new__(m.Handler)

        # Simulate GET /search?q=test
        response_data = []
        def _set_headers(status=200):
            pass
        def _write(data):
            response_data.append(data)

        handler._set_headers = _set_headers
        handler.wfile = MagicMock()
        handler.path = "/search?q=hello"
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        mock_mem.search_memories.assert_called_with("hello")

    def test_handler_get_unknown_path(self, monkeypatch):
        m, mock_mem = _load(monkeypatch)
        handler = object.__new__(m.Handler)
        handler.path = "/unknown"
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        # Should call send_response(404)
        handler.send_response.assert_called_with(404)

    def test_handler_post_add(self, monkeypatch):
        m, mock_mem = _load(monkeypatch)
        handler = object.__new__(m.Handler)
        body = json.dumps({"text": "remember this", "meta": {"source": "cursor"}}).encode("utf-8")
        handler.path = "/add"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = BytesIO(body)
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_POST()
        mock_mem.add_memory.assert_called_with("remember this", metadata={"source": "cursor"})
        handler.send_response.assert_called_with(201)
