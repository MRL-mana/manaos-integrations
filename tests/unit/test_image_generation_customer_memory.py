"""
Unit Tests — image_generation_service.customer_memory
======================================================
CustomerMemory のユニットテスト。MRL Memory をモック。
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.customer_memory import CustomerMemory


class TestDefaultProfile:
    """デフォルトプロファイルテスト"""

    def test_default_profile_structure(self):
        p = CustomerMemory._default_profile("user-1")
        assert p["customer_id"] == "user-1"
        assert p["total_generations"] == 0
        assert p["style_usage"] == {}
        assert p["quality_scores"] == []
        assert p["favorite_prompts"] == []
        assert p["avg_quality"] is None

    def test_default_profile_has_timestamps(self):
        p = CustomerMemory._default_profile("user-2")
        assert "created_at" in p
        assert p["last_active"] is None


class TestRecordGeneration:
    """生成記録テスト"""

    @pytest.fixture
    def cm(self):
        """MRL Memory をモックした CustomerMemory"""
        m = CustomerMemory(memory_url="http://mock:5105")
        # get_profile → デフォルト, save_profile → True
        m.get_profile = AsyncMock(return_value=CustomerMemory._default_profile("test"))
        m.save_profile = AsyncMock(return_value=True)
        return m

    def test_record_increments_count(self, cm):
        asyncio.run(cm.record_generation(
            customer_id="test",
            prompt="sunset",
            style="anime",
            quality_score=7.5,
        ))
        # save_profile が呼ばれたことを確認
        assert cm.save_profile.call_count == 1
        saved = cm.save_profile.call_args[0][1]
        assert saved["total_generations"] == 1

    def test_record_tracks_style(self, cm):
        asyncio.run(cm.record_generation("test", "p1", "anime", 7.0))
        asyncio.run(cm.record_generation("test", "p2", "anime", 8.0))
        asyncio.run(cm.record_generation("test", "p3", "cyberpunk", 6.0))

        # 最後の save を取得
        saved = cm.save_profile.call_args[0][1]
        # 3回呼ばれるが毎回デフォルトプロファイルから始まるので1回ずつ
        assert saved["style_usage"]["cyberpunk"] == 1

    def test_record_saves_quality_scores(self, cm):
        asyncio.run(cm.record_generation("test", "p1", None, 7.5))
        saved = cm.save_profile.call_args[0][1]
        assert len(saved["quality_scores"]) == 1
        assert saved["quality_scores"][0]["score"] == 7.5

    def test_record_saves_favorite_high_rated(self, cm):
        asyncio.run(cm.record_generation(
            "test", "best prompt", "anime", 8.5, rating=5,
        ))
        saved = cm.save_profile.call_args[0][1]
        assert len(saved["favorite_prompts"]) == 1
        assert saved["favorite_prompts"][0]["prompt"] == "best prompt"

    def test_record_skips_favorite_low_rated(self, cm):
        asyncio.run(cm.record_generation(
            "test", "bad prompt", "anime", 3.0, rating=2,
        ))
        saved = cm.save_profile.call_args[0][1]
        assert len(saved["favorite_prompts"]) == 0


class TestSmartDefaults:
    """スマートデフォルトテスト"""

    def test_suggests_favorite_style(self):
        cm = CustomerMemory()
        profile = CustomerMemory._default_profile("user")
        profile["style_usage"] = {"anime": 5, "cyberpunk": 1}
        cm.get_profile = AsyncMock(return_value=profile)

        defaults = asyncio.run(cm.get_smart_defaults("user"))
        assert defaults["suggested_style"] == "anime"

    def test_no_style_suggestion_below_threshold(self):
        cm = CustomerMemory()
        profile = CustomerMemory._default_profile("user")
        profile["style_usage"] = {"anime": 2}
        cm.get_profile = AsyncMock(return_value=profile)

        defaults = asyncio.run(cm.get_smart_defaults("user"))
        assert "suggested_style" not in defaults

    def test_suggests_avg_params(self):
        cm = CustomerMemory()
        profile = CustomerMemory._default_profile("user")
        profile["param_preferences"] = {
            "steps": [20, 20, 30, 30, 25],
            "cfg_scale": [7.0, 7.0, 7.0, 8.0, 8.0],
        }
        cm.get_profile = AsyncMock(return_value=profile)

        defaults = asyncio.run(cm.get_smart_defaults("user"))
        assert defaults["suggested_steps"] == 25.0
        assert defaults["suggested_cfg_scale"] == 7.4

    def test_empty_profile_returns_basics(self):
        cm = CustomerMemory()
        cm.get_profile = AsyncMock(return_value=CustomerMemory._default_profile("user"))

        defaults = asyncio.run(cm.get_smart_defaults("user"))
        assert defaults["total_generations"] == 0
        assert defaults["avg_quality"] is None


class TestCustomerAnalytics:
    """顧客分析テスト"""

    def test_analytics_with_data(self):
        cm = CustomerMemory()
        profile = CustomerMemory._default_profile("user")
        profile["total_generations"] = 10
        profile["avg_quality"] = 7.5
        profile["style_usage"] = {"anime": 6, "cyberpunk": 4}
        profile["quality_scores"] = [
            {"score": s, "at": "2026-01-01"} for s in [6, 7, 8, 7, 8]
        ]
        profile["favorite_prompts"] = [{"prompt": "test"}]
        cm.get_profile = AsyncMock(return_value=profile)

        analytics = asyncio.run(cm.get_customer_analytics("user"))
        assert analytics["total_generations"] == 10
        assert analytics["avg_quality"] == 7.5
        assert "anime" in analytics["style_distribution"]
        assert analytics["style_distribution"]["anime"]["pct"] == 60.0
        assert analytics["favorites_count"] == 1
