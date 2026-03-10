"""
Unit tests for scripts/misc/langchain_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_error_obj = MagicMock()
_error_obj.message = "mocked error"
_error_obj.user_message = "mocked user error"
_meh = MagicMock()
_meh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_error_obj)
))
_meh.ErrorCategory = MagicMock()
_meh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config = MagicMock(return_value={"llm_call": 30, "api_call": 10})
sys.modules.setdefault("manaos_timeout_config", _mtc)

_mcv = MagicMock()
_mcv.ConfigValidator = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_config_validator", _mcv)

_cve = MagicMock()
_cve.ConfigValidatorEnhanced = MagicMock(return_value=MagicMock(
    validate_config_file=MagicMock(return_value=(True, [], {}))
))
sys.modules.setdefault("config_validator_enhanced", _cve)

# _paths
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.OLLAMA_PORT = 11434  # type: ignore
sys.modules["_paths"] = _paths_mod

# langchain / langchain_community
_ollama_cls = MagicMock()
_lc_llms = MagicMock()
_lc_llms.Ollama = _ollama_cls
_lc_community = MagicMock()
_lc_community.llms = _lc_llms
sys.modules.setdefault("langchain_community", _lc_community)
sys.modules.setdefault("langchain_community.llms", _lc_llms)

_lc_core_msgs = MagicMock()
_lc_core_msgs.HumanMessage = MagicMock
_lc_core_msgs.AIMessage = MagicMock
_lc_core_msgs.SystemMessage = MagicMock
sys.modules.setdefault("langchain_core", MagicMock())
sys.modules.setdefault("langchain_core.messages", _lc_core_msgs)

_lc_memory = MagicMock()
_lc_memory.ConversationBufferMemory = MagicMock(return_value=MagicMock())
sys.modules.setdefault("langchain", MagicMock())
sys.modules.setdefault("langchain.memory", _lc_memory)
sys.modules.setdefault("langchain.agents", MagicMock())
sys.modules.setdefault("langchain.tools", MagicMock())
sys.modules.setdefault("langchain.schema", MagicMock())

# langgraph
_sg_cls = MagicMock()
_lg_graph = MagicMock()
_lg_graph.StateGraph = _sg_cls
_lg_graph.END = "END"
_lg_msgs = MagicMock()
sys.modules.setdefault("langgraph", MagicMock())
sys.modules.setdefault("langgraph.graph", _lg_graph)
sys.modules.setdefault("langgraph.graph.message", _lg_msgs)

from scripts.misc.langchain_integration import (
    LangChainIntegration,
    LangGraphIntegration,
    LANGCHAIN_AVAILABLE,
    DEFAULT_OLLAMA_URL,
)


# ─── helpers ──────────────────────────────────────────────────────────────────
def _make_lc() -> LangChainIntegration:
    obj = LangChainIntegration.__new__(LangChainIntegration)
    obj.name = "LangChain"
    obj.logger = MagicMock()
    obj.error_handler = MagicMock(
        handle_exception=MagicMock(return_value=_error_obj)
    )
    obj.timeout_config = {"llm_call": 30, "api_call": 10}  # type: ignore
    obj.ollama_url = DEFAULT_OLLAMA_URL
    obj.model_name = "qwen2.5:7b"
    obj.llm = None
    obj.memory = None
    obj._initialized = False
    return obj


def _make_lg() -> LangGraphIntegration:
    obj = LangGraphIntegration.__new__(LangGraphIntegration)
    obj.name = "LangGraph"
    obj.logger = MagicMock()
    obj.error_handler = MagicMock(
        handle_exception=MagicMock(return_value=_error_obj)
    )
    obj.timeout_config = {"api_call": 10}  # type: ignore
    obj.ollama_url = DEFAULT_OLLAMA_URL
    obj.model_name = "qwen2.5:7b"
    obj.graph = None
    obj._initialized = False
    return obj


# ─── LangChainIntegration ──────────────────────────────────────────────────────
class TestLangChainInit:
    def test_default_attributes(self):
        obj = _make_lc()
        assert obj.ollama_url == DEFAULT_OLLAMA_URL
        assert obj.model_name == "qwen2.5:7b"
        assert obj.llm is None
        assert obj.memory is None

    def test_custom_model_name(self):
        obj = _make_lc()
        obj.model_name = "llama3:8b"
        assert obj.model_name == "llama3:8b"


class TestLangChainCheckAvailability:
    def test_not_available_when_llm_is_none(self):
        obj = _make_lc()
        obj.llm = None
        # _check_availability_internal depends on LANGCHAIN_AVAILABLE and llm
        result = obj._check_availability_internal()
        # LANGCHAIN_AVAILABLE is True (mocked), but llm is None => False
        assert result is False

    def test_available_when_llm_is_set(self):
        obj = _make_lc()
        obj.llm = MagicMock()
        result = obj._check_availability_internal()
        assert result is True


class TestLangChainInitializeLLM:
    def test_success_sets_llm(self):
        obj = _make_lc()
        fake_llm = MagicMock()
        with patch("scripts.misc.langchain_integration.Ollama", return_value=fake_llm):
            result = obj._initialize_llm()
        assert result is True
        assert obj.llm is fake_llm

    def test_exception_returns_false(self):
        obj = _make_lc()
        with patch("scripts.misc.langchain_integration.Ollama", side_effect=RuntimeError("connect error")):
            result = obj._initialize_llm()
        assert result is False
        assert obj.llm is None


class TestLangChainChat:
    def test_returns_none_when_unavailable(self):
        obj = _make_lc()
        obj.llm = None
        with patch.object(obj, "is_available", return_value=False):
            result = obj.chat("hello")
        assert result is None

    def test_returns_response_content(self):
        obj = _make_lc()
        fake_response = MagicMock()
        fake_response.content = "Hi there"
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = fake_response
        obj.llm = fake_llm
        obj.memory = None
        # patch is_available to return True
        with patch.object(obj, "is_available", return_value=True):
            with patch.object(obj, "get_timeout", return_value=30):
                result = obj.chat("hello")
        assert result == "Hi there"

    def test_exception_returns_none(self):
        obj = _make_lc()
        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = RuntimeError("fail")
        obj.llm = fake_llm
        obj.memory = None
        with patch.object(obj, "is_available", return_value=True):
            with patch.object(obj, "get_timeout", return_value=30):
                result = obj.chat("hello")
        assert result is None

    def test_chat_with_system_prompt(self):
        obj = _make_lc()
        fake_response = MagicMock()
        fake_response.content = "response text"
        fake_llm = MagicMock(invoke=MagicMock(return_value=fake_response))
        obj.llm = fake_llm
        obj.memory = None
        with patch.object(obj, "is_available", return_value=True):
            with patch.object(obj, "get_timeout", return_value=30):
                result = obj.chat("hello", system_prompt="You are an assistant")
        assert result == "response text"


# ─── LangGraphIntegration ─────────────────────────────────────────────────────
class TestLangGraphInit:
    def test_default_attributes(self):
        obj = _make_lg()
        assert obj.ollama_url == DEFAULT_OLLAMA_URL
        assert obj.model_name == "qwen2.5:7b"
        assert obj.graph is None


class TestLangGraphCheckAvailability:
    def test_not_available_when_graph_is_none(self):
        obj = _make_lg()
        obj.graph = None
        result = obj._check_availability_internal()
        assert result is False

    def test_available_when_graph_is_set(self):
        obj = _make_lg()
        obj.graph = MagicMock()
        result = obj._check_availability_internal()
        assert result is True


class TestLangGraphInitializeInternal:
    def test_success_creates_graph(self):
        obj = _make_lg()
        fake_graph = MagicMock()
        with patch("scripts.misc.langchain_integration.StateGraph", return_value=fake_graph):
            result = obj._initialize_internal()
        assert result is True
        assert obj.graph is fake_graph

    def test_exception_returns_false(self):
        obj = _make_lg()
        with patch("scripts.misc.langchain_integration.StateGraph", side_effect=RuntimeError("langgraph error")):
            result = obj._initialize_internal()
        assert result is False
