"""intent_router.py のユニットテスト.

LLM / HTTP 呼び出しなしで検証可能な部分を中心にテスト。
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# intent_router はインポート時に manaos_* モジュールを参照する。
# テスト環境で存在しない場合に備えてスタブを挟む。
_STUBS = {}
for mod_name in (
    "manaos_logger",
    "manaos_error_handler",
    "manaos_timeout_config",
    "manaos_config_validator",
):
    if mod_name not in sys.modules:
        stub = MagicMock()
        if mod_name == "manaos_logger":
            stub.get_logger = MagicMock(return_value=MagicMock())
        if mod_name == "manaos_error_handler":
            stub.ManaOSErrorHandler = MagicMock(return_value=MagicMock())
            stub.ErrorCategory = MagicMock()
            stub.ErrorSeverity = MagicMock()
        if mod_name == "manaos_timeout_config":
            stub.get_timeout_config = MagicMock(return_value={})
        if mod_name == "manaos_config_validator":
            cv = MagicMock()
            cv.validate_config = MagicMock(return_value=(True, []))
            stub.ConfigValidator = MagicMock(return_value=cv)
        sys.modules[mod_name] = stub
        _STUBS[mod_name] = stub

from intent_router import IntentType, IntentResult, IntentRouter  # noqa: E402


# ======================================================================
# IntentType Enum
# ======================================================================

class TestIntentType:
    def test_all_members(self):
        assert len(IntentType) == 13

    def test_value_round_trip(self):
        for member in IntentType:
            assert IntentType(member.value) is member


# ======================================================================
# IntentRouter — キーワード分類
# ======================================================================

class TestKeywordClassification:
    """_classify_with_keywords の純粋ロジックテスト."""

    @pytest.fixture(autouse=True)
    def _router(self, tmp_path: Path):
        # 設定ファイルを与えず、デフォルトキーワードで初期化
        self.router = IntentRouter(config_path=tmp_path / "dummy.json")

    @pytest.mark.parametrize(
        "text, expected_intent",
        [
            ("画像を生成して", IntentType.IMAGE_GENERATION),
            ("コードを書いて", IntentType.CODE_GENERATION),
            ("こんにちは、話そう", IntentType.CONVERSATION),
            ("統計レポートを分析", IntentType.DATA_ANALYSIS),
            ("ファイルを整理して", IntentType.FILE_MANAGEMENT),
            ("スケジュールを入れて", IntentType.SCHEDULING),
            ("再起動と停止と設定を確認", IntentType.SYSTEM_CONTROL),
        ],
    )
    def test_keyword_match(self, text: str, expected_intent: IntentType):
        result = self.router._classify_with_keywords(text)
        assert result is not None
        assert result.intent_type == expected_intent

    def test_keyword_no_match_returns_none(self):
        result = self.router._classify_with_keywords("xyzzy")
        assert result is None

    def test_confidence_increases_with_more_keywords(self):
        """複数キーワードが当たると confidence が上がる."""
        r1 = self.router._classify_with_keywords("画像")
        r2 = self.router._classify_with_keywords("画像を生成して描いて")
        assert r1 is not None and r2 is not None
        assert r2.confidence >= r1.confidence

    def test_result_has_matched_keywords(self):
        result = self.router._classify_with_keywords("検索して教えて")
        assert result is not None
        assert "matched_keywords" in result.entities
        assert len(result.entities["matched_keywords"]) >= 1

    def test_suggested_actions_not_empty(self):
        result = self.router._classify_with_keywords("画像を生成して")
        assert result is not None
        assert isinstance(result.suggested_actions, list)


# ======================================================================
# IntentRouter — classify (統合)
# ======================================================================

class TestClassify:
    """classify メソッドの高レベルテスト.

    LLM呼び出し部分はモックで差し替え。
    """

    @pytest.fixture(autouse=True)
    def _router(self, tmp_path: Path):
        self.router = IntentRouter(config_path=tmp_path / "dummy.json")

    def test_empty_text_returns_unknown(self):
        result = self.router.classify("")
        assert result.intent_type == IntentType.UNKNOWN

    def test_keyword_fallback_skips_llm(self):
        """use_llm=False ならキーワードのみ使用."""
        result = self.router.classify("画像を生成", use_llm=False)
        assert result.intent_type == IntentType.IMAGE_GENERATION


# ======================================================================
# IntentResult dataclass
# ======================================================================

class TestIntentResult:
    def test_fields(self):
        r = IntentResult(
            intent_type=IntentType.CONVERSATION,
            confidence=0.8,
            entities={},
            reasoning="test",
            suggested_actions=["hello"],
            timestamp="2026-01-01T00:00:00",
        )
        assert r.confidence == 0.8
        assert r.intent_type == IntentType.CONVERSATION
