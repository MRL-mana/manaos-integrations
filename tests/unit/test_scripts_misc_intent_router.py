"""
Unit tests for scripts/misc/intent_router.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"llm_call": 30.0})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

_paths = MagicMock()
_paths.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths)

sys.modules.setdefault("flask_cors", MagicMock())
sys.modules.setdefault("flask", MagicMock())

import pytest
from scripts.misc.intent_router import (
    IntentResult,
    IntentRouter,
    IntentType,
)


# ── helpers ───────────────────────────────────────────────────────────────

@pytest.fixture
def router(tmp_path):
    return IntentRouter(
        ollama_url="http://127.0.0.1:11434",
        config_path=tmp_path / "config.json",
    )


# ── TestIntentType ────────────────────────────────────────────────────────
class TestIntentType:
    def test_values(self):
        assert IntentType.CONVERSATION.value == "conversation"
        assert IntentType.TASK_EXECUTION.value == "task_execution"
        assert IntentType.UNKNOWN.value == "unknown"

    def test_is_str_subclass(self):
        assert isinstance(IntentType.CONVERSATION, str)


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_default_model(self, router):
        assert "lfm" in router.model

    def test_config_loaded(self, router):
        assert isinstance(router.config, dict)

    def test_keyword_mapping_populated(self, router):
        assert len(router.keyword_mapping) > 0


# ── TestGetDefaultConfig ──────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_has_required_keys(self, router):
        config = router._get_default_config()
        assert "model" in config
        assert "confidence_threshold" in config
        assert "use_keyword_fallback" in config


# ── TestGetDefaultKeywordMapping ──────────────────────────────────────────
class TestGetDefaultKeywordMapping:
    def test_has_conversation_keywords(self, router):
        mapping = router._get_default_keyword_mapping()
        assert IntentType.CONVERSATION in mapping.values()

    def test_has_task_keywords(self, router):
        mapping = router._get_default_keyword_mapping()
        assert IntentType.TASK_EXECUTION in mapping.values()


# ── TestClassifyWithKeywords ──────────────────────────────────────────────
class TestClassifyWithKeywords:
    def test_detects_conversation(self, router):
        result = router._classify_with_keywords("こんにちは、話しかけてみます")
        assert result is not None
        assert result.intent_type == IntentType.CONVERSATION

    def test_detects_task_execution(self, router):
        result = router._classify_with_keywords("タスクを実行してください")
        assert result is not None
        assert result.intent_type == IntentType.TASK_EXECUTION

    def test_detects_information_search(self, router):
        result = router._classify_with_keywords("Pythonについて調べて教えて")
        assert result is not None
        assert result.intent_type == IntentType.INFORMATION_SEARCH

    def test_detects_image_generation(self, router):
        result = router._classify_with_keywords("猫の画像を生成してください")
        assert result is not None
        assert result.intent_type == IntentType.IMAGE_GENERATION

    def test_detects_code_generation(self, router):
        result = router._classify_with_keywords("Pythonのコードを実装して")
        assert result is not None
        assert result.intent_type == IntentType.CODE_GENERATION

    def test_detects_scheduling(self, router):
        result = router._classify_with_keywords("カレンダーにスケジュール追加")
        assert result is not None
        assert result.intent_type == IntentType.SCHEDULING

    def test_no_match_returns_none(self, router):
        result = router._classify_with_keywords("abcdefghijklmnopqrstuvwxyz")
        assert result is None

    def test_confidence_range(self, router):
        result = router._classify_with_keywords("こんにちは")
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_entities_has_matched_keywords(self, router):
        result = router._classify_with_keywords("こんにちは")
        assert result is not None
        assert "matched_keywords" in result.entities


# ── TestFallbackClassification ────────────────────────────────────────────
class TestFallbackClassification:
    def test_returns_unknown(self, router):
        result = router._fallback_classification("some text")
        assert result.intent_type == IntentType.UNKNOWN

    def test_low_confidence(self, router):
        result = router._fallback_classification("some text")
        assert result.confidence < 0.5


# ── TestGetSuggestedActions ───────────────────────────────────────────────
class TestGetSuggestedActions:
    def test_returns_list(self, router):
        for it in IntentType:
            actions = router._get_suggested_actions(it)
            assert isinstance(actions, list)

    def test_conversation_actions(self, router):
        actions = router._get_suggested_actions(IntentType.CONVERSATION)
        assert len(actions) > 0

    def test_unknown_actions(self, router):
        actions = router._get_suggested_actions(IntentType.UNKNOWN)
        assert isinstance(actions, list)


# ── TestClassify ──────────────────────────────────────────────────────────
class TestClassify:
    def test_empty_input_returns_unknown(self, router):
        result = router.classify("")
        assert result.intent_type == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_whitespace_only_returns_unknown(self, router):
        result = router.classify("   ")
        assert result.intent_type == IntentType.UNKNOWN

    def test_keyword_classification_used(self, router):
        result = router.classify("こんにちは", use_llm=False)
        assert result.intent_type == IntentType.CONVERSATION

    def test_returns_intent_result(self, router):
        result = router.classify("画像を生成して")
        assert isinstance(result, IntentResult)

    def test_no_llm_uses_fallback(self, router):
        result = router.classify("aaaaaa", use_llm=False, use_keyword_fallback=False)
        assert result.intent_type == IntentType.UNKNOWN


# ── TestClassifyWithLLM ───────────────────────────────────────────────────
_TEMPLATE = "以下の意図を分類してください。入力: {input}\nJSON形式で回答: {\"intent_type\": \"...\"}"  # noqa


class TestClassifyWithLLM:
    def _router_with_template(self, router):
        router.intent_prompt_template = _TEMPLATE
        return router

    def test_llm_success(self, router):
        router.intent_prompt_template = _TEMPLATE
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": json.dumps({
                "intent_type": "information_search",
                "confidence": 0.85,
                "entities": {"topic": "Python"},
                "reasoning": "検索キーワードを検出",
                "suggested_actions": ["検索を実行"]
            })
        }
        with patch("scripts.misc.intent_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            result = router._classify_with_llm("Pythonについて調べたい")
        assert result.intent_type == IntentType.INFORMATION_SEARCH
        assert result.confidence == 0.85

    def test_llm_http_error_falls_back(self, router):
        router.intent_prompt_template = _TEMPLATE
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("scripts.misc.intent_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            result = router._classify_with_llm("テスト")
        assert result.intent_type == IntentType.UNKNOWN

    def test_llm_exception_falls_back(self, router):
        router.intent_prompt_template = _TEMPLATE
        with patch("scripts.misc.intent_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = Exception("Connection refused")
            result = router._classify_with_llm("テスト")
        assert result.intent_type == IntentType.UNKNOWN

    def test_llm_invalid_json_falls_back(self, router):
        router.intent_prompt_template = _TEMPLATE
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "not JSON at all!"}
        with patch("scripts.misc.intent_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            result = router._classify_with_llm("テスト")
        assert result.intent_type == IntentType.UNKNOWN


# ── TestClassifyBatch ─────────────────────────────────────────────────────
class TestClassifyBatch:
    def test_batch(self, router):
        inputs = ["こんにちは", "画像を生成して", "コードを実装して"]
        results = router.classify_batch(inputs)
        assert len(results) == 3
        assert all(isinstance(r, IntentResult) for r in results)
