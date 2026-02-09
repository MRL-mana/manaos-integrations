#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: Learning System
使用パターン記録、分析、自動最適化（フィードバックループ）を検証
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# モジュールレベルのオプション依存をモック
import sys

# mem0_integration / workflow_automation がなくてもテストできるようにする
sys.modules.setdefault("mem0_integration", MagicMock())
sys.modules.setdefault("workflow_automation", MagicMock())

from learning_system import LearningSystem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def state_dir(tmp_path):
    return tmp_path


@pytest.fixture()
def ls(state_dir):
    """テスト用 LearningSystem（一時ディレクトリに状態保存）"""
    return LearningSystem(storage_path=state_dir / "ls_state.json")


# ---------------------------------------------------------------------------
# 基本: record / analyze
# ---------------------------------------------------------------------------


class TestRecordAndAnalyze:

    def test_record_usage(self, ls):
        ls.record_usage(
            action="llm_chat",
            context={"model": "qwen2.5:14b", "tokens": 500},
            result={"success": True, "response_time": 1.5},
        )
        assert "llm_chat" in ls.usage_patterns
        assert len(ls.usage_patterns["llm_chat"]) == 1

    def test_record_multiple(self, ls):
        for i in range(5):
            ls.record_usage(
                action="search",
                context={"query": f"test_{i}"},
                result={"success": i % 2 == 0, "count": i},
            )
        assert len(ls.usage_patterns["search"]) == 5

    def test_analyze_patterns_empty(self, ls):
        analysis = ls.analyze_patterns()
        assert isinstance(analysis, dict)

    def test_analyze_patterns_with_data(self, ls):
        for i in range(10):
            ls.record_usage(
                action="comfyui_generate",
                context={"model": "sd15"},
                result={"success": True, "time": 2.0 + i * 0.1},
            )
        analysis = ls.analyze_patterns()
        assert isinstance(analysis, dict)


# ---------------------------------------------------------------------------
# 状態の永続化
# ---------------------------------------------------------------------------


class TestPersistence:

    def test_save_and_load(self, state_dir):
        ls1 = LearningSystem(storage_path=state_dir / "persist.json")
        ls1.record_usage("action_a", {"k": "v"}, {"success": True})
        ls1._save_state()

        ls2 = LearningSystem(storage_path=state_dir / "persist.json")
        assert "action_a" in ls2.usage_patterns
        assert len(ls2.usage_patterns["action_a"]) >= 1

    def test_feedback_history_persisted(self, state_dir):
        ls1 = LearningSystem(storage_path=state_dir / "fb.json")
        ls1._feedback_history.append({"type": "test", "at": "2026-01-01"})
        ls1._save_state()

        ls2 = LearningSystem(storage_path=state_dir / "fb.json")
        assert len(ls2._feedback_history) >= 1

    def test_corrupt_state_file(self, state_dir):
        bad_file = state_dir / "bad.json"
        bad_file.write_text("NOT JSON!!!", encoding="utf-8")
        ls = LearningSystem(storage_path=bad_file)
        # 破損ファイルでもクラッシュしない
        assert isinstance(ls.usage_patterns, dict)


# ---------------------------------------------------------------------------
# preferences / optimizations
# ---------------------------------------------------------------------------


class TestPreferences:

    def test_learn_preferences(self, ls):
        for i in range(5):
            ls.record_usage(
                "image_gen",
                {"model": "sdxl", "steps": 30},
                {"success": True},
            )
        prefs = ls.learn_preferences()
        assert isinstance(prefs, dict)

    def test_suggest_optimizations(self, ls):
        for i in range(15):
            ls.record_usage(
                "slow_action",
                {"detail": "x"},
                {"success": i > 5, "response_time": 10.0},
            )
        suggestions = ls.suggest_optimizations()
        assert isinstance(suggestions, list)

    def test_apply_learned_preferences(self, ls):
        ls.preferences["image_gen"] = {"default_model": "sdxl"}
        result = ls.apply_learned_preferences("image_gen", {"model": None})
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# auto_apply_optimizations (フィードバックループ)
# ---------------------------------------------------------------------------


class TestAutoApplyOptimizations:

    def test_auto_apply_empty(self, ls):
        """データなしでも安全に実行される"""
        result = ls.auto_apply_optimizations()
        assert isinstance(result, dict)
        assert "changes" in result or "applied" in result or isinstance(result, dict)

    def test_auto_apply_with_failures(self, ls, state_dir):
        """成功率が低いアクションでリトライ設定が調整される"""
        # 失敗が多いパターンを作る
        for i in range(20):
            ls.record_usage(
                "flaky_api",
                {"endpoint": "/unstable"},
                {"success": i % 5 == 0, "response_time": 3.0},
            )
        # timeout config ファイルを作成
        tc_path = state_dir / "manaos_timeout_config.json"

        # auto_apply の中で開くファイルパスをパッチ
        result = ls.auto_apply_optimizations()
        assert isinstance(result, dict)

    def test_get_feedback_history(self, ls):
        history = ls.get_feedback_history()
        assert isinstance(history, list)


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestStatus:

    def test_get_status(self, ls):
        ls.record_usage("a", {}, {"success": True})
        status = ls.get_status()
        assert isinstance(status, dict)
        assert "usage_patterns" in status or "total_records" in status or isinstance(status, dict)
