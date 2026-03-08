"""
Unit tests for scripts/misc/searxng_llm_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────

# _paths
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.OLLAMA_PORT = 11434
sys.modules["_paths"] = _paths_mod

# searxng_integration
_searxng_cls = MagicMock()
_searxng_mod = MagicMock()
_searxng_mod.SearXNGIntegration = _searxng_cls
sys.modules.setdefault("searxng_integration", _searxng_mod)

# langchain
_tool_cls = MagicMock()
_lc_tools = MagicMock()
_lc_tools.Tool = _tool_cls
sys.modules.setdefault("langchain", MagicMock())
sys.modules.setdefault("langchain.tools", _lc_tools)
sys.modules.setdefault("langchain.agents", MagicMock())
sys.modules.setdefault("langchain.prompts", MagicMock())

# langchain_community
_ollama_cls = MagicMock()
_lc_llms = MagicMock()
_lc_llms.Ollama = _ollama_cls
_lc_community = MagicMock()
_lc_community.llms = _lc_llms
sys.modules.setdefault("langchain_community", _lc_community)
sys.modules.setdefault("langchain_community.llms", _lc_llms)

from scripts.misc.searxng_llm_integration import (
    SearXNGLLMIntegration,
    create_searxng_tool_for_ollama,
    search_for_ollama,
    DEFAULT_OLLAMA_URL,
)


# ─── helpers ──────────────────────────────────────────────────────────────────
def _make_sli() -> SearXNGLLMIntegration:
    obj = SearXNGLLMIntegration.__new__(SearXNGLLMIntegration)
    obj.searxng = MagicMock()
    obj.ollama_url = DEFAULT_OLLAMA_URL
    obj.model_name = "qwen2.5:7b"
    obj.llm = None
    obj.search_tool = None
    return obj


# ─── Init ─────────────────────────────────────────────────────────────────────
class TestSearXNGLLMInit:
    def test_searxng_created(self):
        obj = _make_sli()
        assert obj.searxng is not None

    def test_default_model(self):
        obj = _make_sli()
        assert obj.model_name == "qwen2.5:7b"

    def test_llm_and_tool_none_initially(self):
        obj = _make_sli()
        assert obj.llm is None
        assert obj.search_tool is None


# ─── search_with_llm ──────────────────────────────────────────────────────────
class TestSearchWithLLM:
    def test_returns_search_result_when_no_llm(self):
        obj = _make_sli()
        obj.llm = None
        obj.searxng.search.return_value = {
            "query": "python",
            "results": [{"title": "Python docs", "url": "https://python.org", "content": "..."}],
            "count": 1,
        }
        result = obj.search_with_llm("python", use_llm=False)
        assert result["query"] == "python"
        assert len(result["results"]) == 1

    def test_returns_error_from_searxng(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {"error": "connection refused"}
        result = obj.search_with_llm("test")
        assert result.get("error") == "connection refused"

    def test_adds_llm_summary_when_llm_present(self):
        obj = _make_sli()
        obj.llm = MagicMock()
        obj.llm.invoke.return_value = "要約テキスト"
        obj.searxng.search.return_value = {
            "query": "AI",
            "results": [{"title": "AI news", "url": "http://news.example.com", "content": "AI is great"}],
            "count": 1,
        }
        result = obj.search_with_llm("AI", use_llm=True)
        assert result.get("has_llm_summary") is True
        assert result.get("llm_summary") == "要約テキスト"

    def test_llm_error_sets_has_summary_false(self):
        obj = _make_sli()
        obj.llm = MagicMock()
        obj.llm.invoke.side_effect = RuntimeError("llm error")
        obj.searxng.search.return_value = {
            "query": "test",
            "results": [],
            "count": 0,
        }
        result = obj.search_with_llm("test", use_llm=True)
        assert result.get("has_llm_summary") is False


# ─── get_langchain_tool ────────────────────────────────────────────────────────
class TestGetLangChainTool:
    def test_returns_none_when_not_set(self):
        obj = _make_sli()
        obj.search_tool = None
        assert obj.get_langchain_tool() is None

    def test_returns_tool_when_set(self):
        obj = _make_sli()
        fake_tool = MagicMock()
        obj.search_tool = fake_tool
        assert obj.get_langchain_tool() is fake_tool


# ─── create_rag_context ────────────────────────────────────────────────────────
class TestCreateRAGContext:
    def test_returns_error_string_on_search_error(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {"error": "unreachable"}
        result = obj.create_rag_context("query")
        assert "エラー" in result

    def test_returns_context_string_with_results(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {
            "results": [
                {"title": "Article 1", "url": "http://ex.com/1", "content": "some content"},
            ]
        }
        result = obj.create_rag_context("query", include_urls=True)
        assert "Article 1" in result
        assert "http://ex.com/1" in result

    def test_exclude_urls_when_include_urls_false(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {
            "results": [
                {"title": "Article 2", "url": "http://ex.com/2", "content": "text"},
            ]
        }
        result = obj.create_rag_context("query", include_urls=False)
        assert "http://ex.com/2" not in result


# ─── collect_training_data ─────────────────────────────────────────────────────
class TestCollectTrainingData:
    def test_returns_list_of_data(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {
            "results": [{"title": "T", "url": "http://x.com"}],
            "timestamp": "2024-01-01",
        }
        result = obj.collect_training_data(["q1", "q2"])
        assert len(result) == 2
        assert result[0]["query"] == "q1"

    def test_skips_error_results(self):
        obj = _make_sli()
        obj.searxng.search.return_value = {"error": "fail"}
        result = obj.collect_training_data(["bad query"])
        assert result == []

    def test_saves_to_file(self, tmp_path):
        obj = _make_sli()
        obj.searxng.search.return_value = {
            "results": [{"title": "X", "url": "http://y.com"}],
            "timestamp": "now",
        }
        out_file = str(tmp_path / "data.json")
        result = obj.collect_training_data(["q"], output_file=out_file)
        import os
        assert os.path.exists(out_file)
        assert len(result) == 1


# ─── Standalone functions ──────────────────────────────────────────────────────
class TestCreateSearXNGToolForOllama:
    def test_returns_dict_with_type_function(self):
        fake_instance = MagicMock()
        _searxng_cls.return_value = fake_instance
        result = create_searxng_tool_for_ollama()
        assert isinstance(result, dict)
        assert result.get("type") == "function"
        assert "function" in result

    def test_function_has_name(self):
        fake_instance = MagicMock()
        _searxng_cls.return_value = fake_instance
        result = create_searxng_tool_for_ollama()
        assert result["function"]["name"] == "web_search"


class TestSearchForOllama:
    def test_returns_string_result(self):
        fake_instance = MagicMock()
        fake_instance.search.return_value = {
            "query": "test",
            "count": 1,
            "results": [{"title": "R", "url": "http://r.com", "content": "content"}],
        }
        _searxng_cls.return_value = fake_instance
        result = search_for_ollama("test")
        assert isinstance(result, str)
        assert "test" in result

    def test_returns_error_string_on_error(self):
        fake_instance = MagicMock()
        fake_instance.search.return_value = {"error": "timeout"}
        _searxng_cls.return_value = fake_instance
        result = search_for_ollama("bad query")
        assert "エラー" in result
