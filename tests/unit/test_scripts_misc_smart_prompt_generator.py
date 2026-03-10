"""Tests for scripts/misc/smart_prompt_generator.py"""
import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def _mod():
    # Stub manaos_core_api so the module-level sys.exit(1) is avoided
    manaos_stub = types.ModuleType("manaos_core_api")
    manaos_stub.ManaOSCoreAPI = MagicMock()  # type: ignore
    sys.modules["manaos_core_api"] = manaos_stub

    # Stub dotenv if needed
    if "dotenv" not in sys.modules:
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **kw: None  # type: ignore
        sys.modules["dotenv"] = dotenv_stub

    sys.path.insert(0, "scripts/misc")
    sys.modules.pop("smart_prompt_generator", None)
    with patch("builtins.print"):
        mod = importlib.import_module("smart_prompt_generator")
    return mod


# ---------------------------------------------------------------------------
# Helper: build a mock ManaOSCoreAPI factory
# ---------------------------------------------------------------------------
def _make_manaos_mock(return_value):
    """Return a class-like mock whose instances return `return_value` from .act()"""
    instance = MagicMock()
    instance.act.return_value = return_value
    cls = MagicMock(return_value=instance)
    return cls


# ---------------------------------------------------------------------------
# search_prompt_references
# ---------------------------------------------------------------------------
class TestSearchPromptReferences:
    def test_returns_list_on_success(self, _mod, monkeypatch):
        mock_result = {
            "status": "success",
            "results": [
                {"title": "T1", "url": "https://example.com/1", "description": "desc1"},
                {"title": "T2", "url": "https://example.com/2", "description": "desc2"},
            ]
        }
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        refs = _mod.search_prompt_references("cute cat", count=2)
        assert isinstance(refs, list)
        assert len(refs) == 2
        assert refs[0]["title"] == "T1"

    def test_returns_empty_when_no_results(self, _mod, monkeypatch):
        mock_result = {"status": "success", "results": []}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        refs = _mod.search_prompt_references("anything")
        assert refs == []

    def test_returns_empty_on_exception(self, _mod, monkeypatch):
        cls = MagicMock(side_effect=RuntimeError("network error"))
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", cls)
        refs = _mod.search_prompt_references("anything")
        assert refs == []

    def test_returns_empty_when_status_not_success(self, _mod, monkeypatch):
        mock_result = {"status": "error"}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        refs = _mod.search_prompt_references("anything")
        assert refs == []


# ---------------------------------------------------------------------------
# generate_prompt_with_ai
# ---------------------------------------------------------------------------
class TestGeneratePromptWithAi:
    def test_returns_string_on_success(self, _mod, monkeypatch):
        mock_result = {"result": {"response": "anime girl, detailed background"}}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        result = _mod.generate_prompt_with_ai("anime girl", style="watercolor")
        assert result == "anime girl, detailed background"

    def test_strips_prompt_label(self, _mod, monkeypatch):
        mock_result = {"result": {"response": "プロンプト: beautiful landscape"}}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        result = _mod.generate_prompt_with_ai("landscape")
        assert result == "beautiful landscape"

    def test_strips_surrounding_quotes(self, _mod, monkeypatch):
        mock_result = {"result": {"response": '"cat sitting on a bench"'}}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        result = _mod.generate_prompt_with_ai("cat")
        assert result == "cat sitting on a bench"

    def test_returns_none_on_exception(self, _mod, monkeypatch):
        cls = MagicMock(side_effect=RuntimeError("ai down"))
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", cls)
        result = _mod.generate_prompt_with_ai("cat")
        assert result is None

    def test_returns_none_when_no_response(self, _mod, monkeypatch):
        mock_result = {"result": {}}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        result = _mod.generate_prompt_with_ai("cat")
        assert result is None


# ---------------------------------------------------------------------------
# improve_prompt_with_ai
# ---------------------------------------------------------------------------
class TestImprovePromptWithAi:
    def test_returns_improved_string(self, _mod, monkeypatch):
        mock_result = {"result": {"response": "improved prompt text"}}
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", _make_manaos_mock(mock_result))
        result = _mod.improve_prompt_with_ai("simple prompt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_original_on_exception(self, _mod, monkeypatch):
        # improve_prompt_with_ai falls back to returning the original prompt on error
        cls = MagicMock(side_effect=RuntimeError("error"))
        monkeypatch.setattr(_mod, "ManaOSCoreAPI", cls)
        result = _mod.improve_prompt_with_ai("my original prompt")
        assert result == "my original prompt"
