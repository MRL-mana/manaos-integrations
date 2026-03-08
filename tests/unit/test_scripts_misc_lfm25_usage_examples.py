"""Tests for scripts/misc/lfm25_usage_examples.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_llm_stubs(monkeypatch):
    # AlwaysReadyLLMClient stub
    mock_resp = MagicMock()
    mock_resp.response = "test response"
    mock_resp.latency_ms = 100.0
    mock_client = MagicMock()
    mock_client.chat.return_value = mock_resp
    mock_client.ask.return_value = mock_resp

    arlc_mod = types.ModuleType("always_ready_llm_client")
    arlc_mod.AlwaysReadyLLMClient = MagicMock(return_value=mock_client)
    arlc_mod.ModelType = MagicMock()
    arlc_mod.TaskType = MagicMock()
    monkeypatch.setitem(sys.modules, "always_ready_llm_client", arlc_mod)

    # LLMRouter stub
    mock_router_resp = MagicMock()
    mock_router_resp.response = "routed"
    mock_router_resp.latency_ms = 50.0
    mock_router = MagicMock()
    mock_router.route.return_value = mock_router_resp
    llm_mod = types.ModuleType("llm_routing")
    llm_mod.LLMRouter = MagicMock(return_value=mock_router)
    monkeypatch.setitem(sys.modules, "llm_routing", llm_mod)

    paths_mod = types.ModuleType("_paths")
    paths_mod.UNIFIED_API_PORT = 9502
    monkeypatch.setitem(sys.modules, "_paths", paths_mod)
    monkeypatch.setitem(sys.modules, "manaos_integrations._paths", paths_mod)

    return mock_client, mock_router


def _prep(monkeypatch):
    sys.modules.pop("lfm25_usage_examples", None)
    client, router = _make_llm_stubs(monkeypatch)
    monkeypatch.syspath_prepend(str(_MISC))
    import lfm25_usage_examples as m
    return m, client, router


class TestLfm25UsageExamplesImport:
    def test_imports(self, monkeypatch):
        m, _, _ = _prep(monkeypatch)
        assert "lfm25_usage_examples" in sys.modules

    def test_has_example_functions(self, monkeypatch):
        m, _, _ = _prep(monkeypatch)
        for i in range(1, 6):
            assert callable(getattr(m, f"example_{i}_" + {
                1: "basic_chat", 2: "lightweight_conversation",
                3: "draft_creation", 4: "text_organization", 5: "llm_routing"
            }[i]))


class TestExampleFunctions:
    def test_example1_basic_chat(self, monkeypatch):
        m, client, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_1_basic_chat()
        client.chat.assert_called()

    def test_example2_lightweight_conversation(self, monkeypatch):
        m, client, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_2_lightweight_conversation()
        client.chat.assert_called()

    def test_example3_draft_creation(self, monkeypatch):
        m, client, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_3_draft_creation()
        client.chat.assert_called()

    def test_example4_text_organization(self, monkeypatch):
        m, client, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_4_text_organization()
        client.chat.assert_called()

    def test_example5_llm_routing(self, monkeypatch):
        m, _, router = _prep(monkeypatch)
        with patch("builtins.print"):
            m.example_5_llm_routing()
        # router.route or client called
