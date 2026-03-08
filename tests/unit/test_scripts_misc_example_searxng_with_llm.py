"""Tests for scripts/misc/example_searxng_with_llm.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub():
    mod = types.ModuleType("_paths")
    mod.OLLAMA_PORT = 11434
    mod.SEARXNG_PORT = 8080
    return mod


def _make_searxng_stub():
    mod = types.ModuleType("searxng_llm_integration")
    inst = MagicMock()
    inst.search_with_llm.return_value = {"results": [], "llm_summary": "test"}
    inst.create_rag_context.return_value = "rag context"
    inst.collect_training_data.return_value = []
    mod.SearXNGLLMIntegration = MagicMock(return_value=inst)
    mod.search_for_ollama = MagicMock(return_value={"results": []})
    mod.create_searxng_tool_for_ollama = MagicMock(return_value=lambda q: {})
    return mod, inst


def _prep(monkeypatch):
    sys.modules.pop("example_searxng_with_llm", None)
    sys.modules.pop("manaos_integrations._paths", None)
    sys.modules.setdefault("_paths", _make_paths_stub())
    searxng_mod, inst = _make_searxng_stub()
    monkeypatch.setitem(sys.modules, "searxng_llm_integration", searxng_mod)
    monkeypatch.syspath_prepend(str(_MISC))
    import example_searxng_with_llm as m
    return m, inst


class TestExampleSearxngWithLlmImport:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "example_searxng_with_llm" in sys.modules

    def test_has_example_functions(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert callable(m.example_1_simple_search_with_llm)
        assert callable(m.example_2_rag_context)

    def test_ollama_url_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        m, _ = _prep(monkeypatch)
        assert "11434" in m.DEFAULT_OLLAMA_URL

    def test_ollama_url_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_URL", "http://custom:9999")
        sys.modules.pop("example_searxng_with_llm", None)
        m, _ = _prep(monkeypatch)
        assert m.DEFAULT_OLLAMA_URL == "http://custom:9999"


class TestExampleFunctions:
    def test_example1_runs(self, monkeypatch):
        m, inst = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_1_simple_search_with_llm()
        inst.search_with_llm.assert_called_once()

    def test_example2_runs(self, monkeypatch):
        m, inst = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_2_rag_context()
        inst.create_rag_context.assert_called_once()

    def test_example1_uses_query(self, monkeypatch):
        m, inst = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_1_simple_search_with_llm()
        call_kwargs = inst.search_with_llm.call_args
        assert call_kwargs is not None
