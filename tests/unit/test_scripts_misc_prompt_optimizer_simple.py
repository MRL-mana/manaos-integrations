"""
Unit tests for scripts/misc/prompt_optimizer_simple.py
"""
import sys
from unittest.mock import MagicMock

# manaos_logger mock
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

import pytest
from scripts.misc.prompt_optimizer_simple import (
    SimplePromptOptimizer,
    optimize_prompt,
)


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_optimization_enabled_by_default(self):
        o = SimplePromptOptimizer()
        assert o.enable_optimization is True

    def test_can_disable_optimization(self):
        o = SimplePromptOptimizer(enable_optimization=False)
        assert o.enable_optimization is False

    def test_rules_loaded(self):
        o = SimplePromptOptimizer()
        assert isinstance(o.optimization_rules, dict)
        assert "rag_enhancements" in o.optimization_rules


# ── TestLoadOptimizationRules ──────────────────────────────────────────────
class TestLoadOptimizationRules:
    def test_has_rag_enhancements(self):
        o = SimplePromptOptimizer()
        assert isinstance(o.optimization_rules["rag_enhancements"], list)
        assert len(o.optimization_rules["rag_enhancements"]) > 0

    def test_has_japanese_optimizations(self):
        o = SimplePromptOptimizer()
        assert "japanese_optimizations" in o.optimization_rules

    def test_has_query_expansions(self):
        o = SimplePromptOptimizer()
        assert "query_expansions" in o.optimization_rules


# ── TestOptimizeDisabled ───────────────────────────────────────────────────
class TestOptimizeDisabled:
    def test_returns_original_when_disabled(self):
        o = SimplePromptOptimizer(enable_optimization=False)
        result = o.optimize("hello")
        assert result["optimized_prompt"] == "hello"

    def test_optimized_false_when_disabled(self):
        o = SimplePromptOptimizer(enable_optimization=False)
        result = o.optimize("hello")
        assert result["optimized"] is False

    def test_changes_empty_when_disabled(self):
        o = SimplePromptOptimizer(enable_optimization=False)
        result = o.optimize("hello")
        assert result["changes"] == []

    def test_original_prompt_preserved(self):
        o = SimplePromptOptimizer(enable_optimization=False)
        result = o.optimize("my prompt")
        assert result["original_prompt"] == "my prompt"


# ── TestOptimizeResult ─────────────────────────────────────────────────────
class TestOptimizeResult:
    def test_returns_dict(self):
        o = SimplePromptOptimizer()
        result = o.optimize("テストの質問")
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        o = SimplePromptOptimizer()
        result = o.optimize("テストの質問")
        for key in ("optimized", "original_prompt", "optimized_prompt", "changes", "task_type"):
            assert key in result

    def test_original_prompt_unchanged(self):
        o = SimplePromptOptimizer()
        result = o.optimize("テストの質問")
        assert result["original_prompt"] == "テストの質問"

    def test_task_type_stored(self):
        o = SimplePromptOptimizer()
        result = o.optimize("質問", task_type="chat")
        assert result["task_type"] == "chat"


# ── TestOptimizeForRag ────────────────────────────────────────────────────
class TestOptimizeForRag:
    def test_short_prompt_expanded(self):
        o = SimplePromptOptimizer()
        result, changes = o._optimize_for_rag("短い")
        assert len(result) > 10
        assert any("拡張" in c for c in changes)

    def test_long_prompt_not_expanded(self):
        o = SimplePromptOptimizer()
        long_prompt = "これは十分に長いプロンプトです。もっと長くしましょう。こ"
        result, changes = o._optimize_for_rag(long_prompt)
        # No "短いプロンプト" expansion change
        assert not any("短い" in c and "拡張" in c for c in changes)

    def test_context_instruction_added_when_missing(self):
        o = SimplePromptOptimizer()
        result, changes = o._optimize_for_rag("具体的な長めの質問文です。詳しく教えてください。")
        # コンテキスト指示が追加される
        assert any("コンテキスト" in c for c in changes)

    def test_context_instruction_not_added_when_present(self):
        o = SimplePromptOptimizer()
        prompt = "コンテキストをもとに答えてください。長めの質問です。追加情報あり。"
        result, changes = o._optimize_for_rag(prompt)
        # Already has コンテキスト, so no addition
        assert not any("コンテキスト優先" in c for c in changes)

    def test_returns_tuple(self):
        o = SimplePromptOptimizer()
        result = o._optimize_for_rag("テスト")
        assert isinstance(result, tuple)
        assert len(result) == 2


# ── TestOptimizeJapanese ──────────────────────────────────────────────────
class TestOptimizeJapanese:
    def test_returns_tuple(self):
        o = SimplePromptOptimizer()
        result, changes = o._optimize_japanese("テスト")
        assert isinstance(changes, list)

    def test_returns_same_string(self):
        o = SimplePromptOptimizer()
        result, _ = o._optimize_japanese("テスト")
        assert result == "テスト"


# ── TestExpandQuery ───────────────────────────────────────────────────────
class TestExpandQuery:
    def test_returns_tuple(self):
        o = SimplePromptOptimizer()
        result, changes = o._expand_query("短い")
        assert isinstance(changes, list)

    def test_returns_string(self):
        o = SimplePromptOptimizer()
        result, _ = o._expand_query("テスト")
        assert isinstance(result, str)


# ── TestImproveClarity ────────────────────────────────────────────────────
class TestImproveClarity:
    def test_returns_tuple(self):
        o = SimplePromptOptimizer()
        result, changes = o._improve_clarity("これはテストです")
        assert isinstance(changes, list)

    def test_prompt_returned(self):
        o = SimplePromptOptimizer()
        result, _ = o._improve_clarity("これはテストです")
        assert isinstance(result, str)


# ── TestOptimizePromptFunction ─────────────────────────────────────────────
class TestOptimizePromptFunction:
    def test_returns_string(self):
        result = optimize_prompt("テスト")
        assert isinstance(result, str)

    def test_disabled_returns_original(self):
        result = optimize_prompt("テスト", enable=False)
        assert result == "テスト"

    def test_rag_task_type(self):
        result = optimize_prompt("テスト", task_type="rag")
        assert isinstance(result, str)
        # Short prompt should be expanded
        assert len(result) > len("テスト")
