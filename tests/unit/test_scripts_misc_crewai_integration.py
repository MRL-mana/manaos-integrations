"""
Unit tests for scripts/misc/crewai_integration.py
"""
import sys
import importlib
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
_mtc.get_timeout_config = MagicMock(
    return_value={"api_call": 10, "workflow_execution": 60}
)
sys.modules.setdefault("manaos_timeout_config", _mtc)

_mcv = MagicMock()
_mcv.ConfigValidator = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_config_validator", _mcv)

_cve = MagicMock()
_cve.ConfigValidatorEnhanced = MagicMock(return_value=MagicMock(
    validate_config_file=MagicMock(return_value=(True, [], {}))
))
sys.modules.setdefault("config_validator_enhanced", _cve)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.OLLAMA_PORT = 11434
sys.modules["_paths"] = _paths_mod

# crewai / crewai_tools / langchain
_mock_agent_cls = MagicMock()
_mock_task_cls = MagicMock()
_mock_crew_cls = MagicMock()
_mock_process = MagicMock()

_crewai_mod = MagicMock()
_crewai_mod.Agent = _mock_agent_cls
_crewai_mod.Task = _mock_task_cls
_crewai_mod.Crew = _mock_crew_cls
_crewai_mod.Process = _mock_process
sys.modules["crewai"] = _crewai_mod

_crewai_tools_mod = MagicMock()
_crewai_tools_mod.tool = lambda f: f  # pass-through decorator
sys.modules["crewai_tools"] = _crewai_tools_mod

_ollama_mock = MagicMock()
_lc_llms = MagicMock()
_lc_llms.Ollama = _ollama_mock
_lc_community = MagicMock()
_lc_community.llms = _lc_llms
sys.modules["langchain_community"] = _lc_community
sys.modules["langchain_community.llms"] = _lc_llms

from scripts.misc.crewai_integration import (
    CrewAIIntegration,
    CREWAI_AVAILABLE,
    LANGCHAIN_AVAILABLE,
    DEFAULT_OLLAMA_URL,
)


# ── helpers ────────────────────────────────────────────────────────────────
def _make_integration(url: str = "http://localhost:11434") -> CrewAIIntegration:
    return CrewAIIntegration(ollama_url=url)


def _make_available_integration() -> CrewAIIntegration:
    """llm を設定済みの利用可能インスタンスを返す。"""
    ci = _make_integration()
    ci.llm = MagicMock()
    return ci


# ── TestModuleFlags ────────────────────────────────────────────────────────
class TestModuleFlags:
    def test_crewai_available_true_when_mocked(self):
        assert CREWAI_AVAILABLE is True

    def test_langchain_available_true_when_mocked(self):
        assert LANGCHAIN_AVAILABLE is True

    def test_default_url_contains_ollama_port(self):
        assert "11434" in DEFAULT_OLLAMA_URL


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_stores_url_and_model(self):
        ci = CrewAIIntegration(
            ollama_url="http://localhost:9999",
            model_name="llama3:8b"
        )
        assert ci.ollama_url == "http://localhost:9999"
        assert ci.model_name == "llama3:8b"

    def test_llm_initially_none(self):
        ci = _make_integration()
        assert ci.llm is None


# ── TestInitializeLLM ──────────────────────────────────────────────────────
class TestInitializeLLM:
    def test_returns_true_and_sets_llm_on_success(self):
        ci = _make_integration()
        mock_llm_instance = MagicMock()
        with patch("scripts.misc.crewai_integration.Ollama", return_value=mock_llm_instance):
            result = ci._initialize_llm()
        assert result is True
        assert ci.llm is mock_llm_instance

    def test_returns_false_on_exception(self):
        ci = _make_integration()
        with patch("scripts.misc.crewai_integration.Ollama", side_effect=Exception("fail")):
            result = ci._initialize_llm()
        assert result is False
        assert ci.llm is None


# ── TestInitializeInternal ─────────────────────────────────────────────────
class TestInitializeInternal:
    def test_calls_initialize_llm(self):
        ci = _make_integration()
        with patch.object(ci, "_initialize_llm", return_value=True) as mock_init:
            result = ci._initialize_internal()
        assert result is True
        mock_init.assert_called_once()

    def test_returns_false_when_crewai_unavailable(self):
        ci = _make_integration()
        with patch("scripts.misc.crewai_integration.CREWAI_AVAILABLE", False):
            result = ci._initialize_internal()
        assert result is False

    def test_returns_false_when_langchain_unavailable(self):
        ci = _make_integration()
        with patch("scripts.misc.crewai_integration.LANGCHAIN_AVAILABLE", False):
            result = ci._initialize_internal()
        assert result is False


# ── TestCheckAvailabilityInternal ──────────────────────────────────────────
class TestCheckAvailabilityInternal:
    def test_false_when_llm_is_none(self):
        ci = _make_integration()
        assert ci._check_availability_internal() is False

    def test_true_when_all_available(self):
        ci = _make_available_integration()
        result = ci._check_availability_internal()
        assert result is True

    def test_false_when_crewai_unavailable(self):
        ci = _make_available_integration()
        with patch("scripts.misc.crewai_integration.CREWAI_AVAILABLE", False):
            result = ci._check_availability_internal()
        assert result is False


# ── TestCreateAgent ────────────────────────────────────────────────────────
class TestCreateAgent:
    def test_returns_none_when_unavailable(self):
        ci = _make_integration()
        with patch.object(ci, "is_available", return_value=False):
            result = ci.create_agent("Researcher", "find info")
        assert result is None

    def test_returns_agent_when_available(self):
        ci = _make_available_integration()
        mock_agent = MagicMock()
        with patch("scripts.misc.crewai_integration.Agent", return_value=mock_agent):
            result = ci.create_agent("Researcher", "find info")
        assert result is mock_agent

    def test_returns_none_on_exception(self):
        ci = _make_available_integration()
        with patch("scripts.misc.crewai_integration.Agent", side_effect=Exception("err")):
            result = ci.create_agent("Researcher", "find info")
        assert result is None

    def test_includes_search_tool_when_requested(self):
        ci = _make_available_integration()
        mock_search_tool = MagicMock()
        ci.get_searxng_tool = MagicMock(return_value=mock_search_tool)
        captured_tools = []
        def _capture_agent(**kwargs):
            captured_tools.extend(kwargs.get("tools", []))
            return MagicMock()
        with patch("scripts.misc.crewai_integration.Agent", side_effect=_capture_agent):
            ci.create_agent("R", "g", include_search=True)
        assert mock_search_tool in captured_tools


# ── TestCreateTask ─────────────────────────────────────────────────────────
class TestCreateTask:
    def test_returns_none_when_unavailable(self):
        ci = _make_integration()
        with patch.object(ci, "is_available", return_value=False):
            result = ci.create_task("Do something", agent=MagicMock())
        assert result is None

    def test_returns_task_when_available(self):
        ci = _make_available_integration()
        mock_task = MagicMock()
        with patch("scripts.misc.crewai_integration.Task", return_value=mock_task):
            result = ci.create_task("Analyze data", agent=MagicMock())
        assert result is mock_task

    def test_returns_none_on_exception(self):
        ci = _make_available_integration()
        with patch("scripts.misc.crewai_integration.Task", side_effect=Exception("err")):
            result = ci.create_task("desc", agent=MagicMock())
        assert result is None


# ── TestExecuteCrew ────────────────────────────────────────────────────────
class TestExecuteCrew:
    def test_returns_none_when_unavailable(self):
        ci = _make_integration()
        with patch.object(ci, "is_available", return_value=False):
            result = ci.execute_crew([MagicMock()], [MagicMock()])
        assert result is None

    def test_returns_result_dict_on_success(self):
        ci = _make_available_integration()
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "crew result string"
        with patch("scripts.misc.crewai_integration.Crew", return_value=mock_crew_instance):
            result = ci.execute_crew([MagicMock()], [MagicMock()])
        assert result is not None
        assert "result" in result
        assert result["tasks_completed"] == 1

    def test_returns_none_on_exception(self):
        ci = _make_available_integration()
        with patch("scripts.misc.crewai_integration.Crew", side_effect=Exception("err")):
            result = ci.execute_crew([MagicMock()], [MagicMock()])
        assert result is None

    def test_tasks_completed_count_is_correct(self):
        ci = _make_available_integration()
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "done"
        with patch("scripts.misc.crewai_integration.Crew", return_value=mock_crew_instance):
            result = ci.execute_crew(
                [MagicMock(), MagicMock()],
                [MagicMock(), MagicMock(), MagicMock()]
            )
        assert result["tasks_completed"] == 3
