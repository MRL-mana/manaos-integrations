#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM修正の動作確認テスト（pytest 形式）

Ollama が利用不可の環境では pytest.skip する。
"""

import sys
import pytest

# ──────────────────────────────────────────
# クライアント可用性チェック（モジュールロード時に sys.exit しない）
# ──────────────────────────────────────────
try:
    from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
    _LLM_AVAILABLE = True
except Exception as _import_err:
    _LLM_AVAILABLE = False
    _import_err_msg = str(_import_err)


def _require_llm():
    """LLM が使えない環境ではスキップ"""
    if not _LLM_AVAILABLE:
        pytest.skip(f"always_ready_llm_client unavailable: {_import_err_msg}")


# ──────────────────────────────────────────
# テスト
# ──────────────────────────────────────────

class TestLLMClientFix:
    """LLMクライアント修正の動作確認"""

    def test_import(self):
        """テスト1: LLMクライアントのインポート"""
        _require_llm()
        assert AlwaysReadyLLMClient is not None  # type: ignore[possibly-unbound]

    def test_model_types(self):
        """テスト2: ModelType 定数の存在確認"""
        _require_llm()
        assert hasattr(ModelType, "LIGHT")  # type: ignore[possibly-unbound]
        assert hasattr(ModelType, "MEDIUM")  # type: ignore[possibly-unbound]
        assert hasattr(ModelType, "HEAVY")  # type: ignore[possibly-unbound]
        assert hasattr(ModelType, "REASONING")  # type: ignore[possibly-unbound]

    def test_client_init(self):
        """テスト3: クライアントの初期化"""
        _require_llm()
        client = AlwaysReadyLLMClient(use_cache=False)  # type: ignore[possibly-unbound]
        assert client is not None

    @pytest.mark.slow
    def test_llm_call(self):
        """テスト4: LLM 呼び出し（実 Ollama 必要）"""
        _require_llm()
        client = AlwaysReadyLLMClient(use_cache=False)  # type: ignore[possibly-unbound]
        try:
            response = client.chat(
                "こんにちは",
                model=ModelType.MEDIUM,  # type: ignore[possibly-unbound]
                task_type=TaskType.CONVERSATION,  # type: ignore[possibly-unbound]
            )
            assert response is not None
            assert hasattr(response, "response")
            assert hasattr(response, "latency_ms")
        except Exception as e:
            err = str(e)
            if "404" in err or "Ollama" in err or "LLM" in err or "connect" in err.lower():
                pytest.skip(f"Ollama 未起動またはモデル未ロード: {err}")
            raise

    def test_slack_llm_flag(self):
        """テスト5: Slack統合の LLM_AVAILABLE フラグ"""
        _require_llm()
        import logging
        old_level = logging.root.level
        logging.root.setLevel(logging.CRITICAL)
        try:
            import slack_integration
            # LLM_AVAILABLE 属性が True/False いずれかに設定されているか、なければ skip
            # slack_integration はサブパッケージなので slack_integration.slack_integration も確認
            llm_available = getattr(slack_integration, "LLM_AVAILABLE", None)
            if llm_available is None:
                try:
                    import slack_integration.slack_integration as _si_mod
                    llm_available = getattr(_si_mod, "LLM_AVAILABLE", None)
                except Exception:
                    pass
            if llm_available is None:
                pytest.skip("slack_integration has no LLM_AVAILABLE attribute")
            assert isinstance(llm_available, bool)
        except ImportError:
            pytest.skip("slack_integration unavailable")
        finally:
            logging.root.setLevel(old_level)
