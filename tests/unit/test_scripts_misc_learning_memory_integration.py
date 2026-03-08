"""Tests for scripts/misc/learning_memory_integration.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_stubs(monkeypatch):
    for name, cls_names in [
        ("manaos_logger", ["get_logger", "get_service_logger"]),
        ("manaos_error_handler", ["ManaOSErrorHandler", "ErrorCategory", "ErrorSeverity"]),
        ("rag_memory_optimized", ["RAGMemoryOptimized"]),
        ("learning_system", ["LearningSystem"]),
        ("unified_cache_system", ["get_unified_cache"]),
    ]:
        mod = types.ModuleType(name)
        for cls_name in cls_names:
            setattr(mod, cls_name, MagicMock())
        monkeypatch.setitem(sys.modules, name, mod)


def _prep(monkeypatch):
    sys.modules.pop("learning_memory_integration", None)
    _make_stubs(monkeypatch)
    monkeypatch.syspath_prepend(str(_MISC))
    import learning_memory_integration as m
    return m


class TestLearningMemoryIntegrationImport:
    def test_imports(self, monkeypatch):
        m = _prep(monkeypatch)
        assert hasattr(m, "LearningMemoryIntegration")

    def test_instantiation(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.LearningMemoryIntegration()
        assert obj is not None


class TestRecordAndLearn:
    def _obj(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.LearningMemoryIntegration()
        obj.learning = MagicMock()
        obj.memory = MagicMock()
        return obj

    def test_records_usage(self, monkeypatch):
        obj = self._obj(monkeypatch)
        obj.record_and_learn("test_action", {"key": "val"}, {"status": "success"})
        obj.learning.record_usage.assert_called_once_with(
            "test_action", {"key": "val"}, {"status": "success"}
        )

    def test_saves_to_memory_on_success(self, monkeypatch):
        obj = self._obj(monkeypatch)
        obj.record_and_learn("act", {}, {"status": "success"}, save_to_memory=True)
        obj.memory.add_memory.assert_called_once()

    def test_no_memory_save_on_failure(self, monkeypatch):
        obj = self._obj(monkeypatch)
        obj.record_and_learn("act", {}, {"status": "error"}, save_to_memory=True)
        obj.memory.add_memory.assert_not_called()

    def test_no_memory_save_when_flag_false(self, monkeypatch):
        obj = self._obj(monkeypatch)
        obj.record_and_learn("act", {}, {"status": "success"}, save_to_memory=False)
        obj.memory.add_memory.assert_not_called()


class TestCalculateImportanceFromResult:
    def _obj(self, monkeypatch):
        m = _prep(monkeypatch)
        return m.LearningMemoryIntegration()

    def test_success_increases_importance(self, monkeypatch):
        obj = self._obj(monkeypatch)
        base = obj._calculate_importance_from_result({})
        success_val = obj._calculate_importance_from_result({"status": "success"})
        assert success_val > base

    def test_error_increases_importance(self, monkeypatch):
        obj = self._obj(monkeypatch)
        base = obj._calculate_importance_from_result({})
        error_val = obj._calculate_importance_from_result({"error": "something"})
        assert error_val > base

    def test_value_clamped_to_1(self, monkeypatch):
        obj = self._obj(monkeypatch)
        val = obj._calculate_importance_from_result({"status": "success", "error": "also"})
        assert val <= 1.0

    def test_value_non_negative(self, monkeypatch):
        obj = self._obj(monkeypatch)
        assert obj._calculate_importance_from_result({}) >= 0.0


class TestGetLearnedPreferences:
    def test_calls_learn_preferences(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.LearningMemoryIntegration()
        obj.learning = MagicMock()
        obj.learning.learn_preferences.return_value = {"pref": "x"}
        result = obj.get_learned_preferences()
        obj.learning.learn_preferences.assert_called_once()
        assert result == {"pref": "x"}


class TestAnalyzeAndOptimize:
    def test_returns_dict(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.LearningMemoryIntegration()
        obj.learning = MagicMock()
        obj.learning.analyze_patterns.return_value = {"recommendations": []}
        result = obj.analyze_and_optimize()
        assert isinstance(result, dict)

    def test_analyze_patterns_error_handled(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.LearningMemoryIntegration()
        obj.learning = MagicMock()
        obj.learning.analyze_patterns.side_effect = RuntimeError("fail")
        result = obj.analyze_and_optimize()
        assert isinstance(result, dict)
