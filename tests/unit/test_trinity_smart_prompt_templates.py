"""Unit tests for tools/trinity_smart_prompt_templates.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_smart_prompt_templates import SmartPromptTemplates


def _make_spt() -> SmartPromptTemplates:
    """ファイル保存をモックしてインスタンスを生成するヘルパー。"""
    with patch.object(SmartPromptTemplates, "_save_history", return_value=None), \
         patch.object(SmartPromptTemplates, "_save_favorites", return_value=None):
        spt = SmartPromptTemplates()
    return spt


# ─────────────────────────────────────────────────────────────────────────────
# generate_prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestGeneratePrompt:
    def test_custom_elements_used_in_prompt(self):
        # アニメテンプレート: quality・mood キーはプレースホルダーと一致するので置換される。
        # （"styles" キーは "a ..., {style}, ..." プレースホルダーと名前がズレるため置換対象外）
        spt = _make_spt()
        result = spt.generate_prompt(
            "anime",
            custom_elements={"quality": "masterpiece", "mood": "smiling"},
        )
        assert "masterpiece" in result
        assert "smiling" in result

    def test_fantasy_custom_elements_all_match(self):
        # fantasy テンプレートはキー名とプレースホルダーが完全一致するため確実に置換される。
        spt = _make_spt()
        result = spt.generate_prompt(
            "fantasy",
            custom_elements={
                "character_type": "dragon",
                "magical_elements": "sparkling effects",
                "setting": "enchanted garden",
                "quality": "mystical",
            },
        )
        assert "dragon" in result
        assert "sparkling effects" in result
        assert "enchanted garden" in result
        assert "mystical" in result

    def test_unknown_category_returns_default(self):
        spt = _make_spt()
        result = spt.generate_prompt("nonexistent_category")
        assert result == "a beautiful image, high quality"

    def test_all_categories_return_non_empty(self):
        spt = _make_spt()
        import random
        random.seed(42)
        for category in ["anime", "realistic", "fantasy", "cyberpunk", "nature"]:
            result = spt.generate_prompt(category)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_realistic_custom_lighting_used(self):
        spt = _make_spt()
        result = spt.generate_prompt(
            "realistic",
            custom_elements={
                "style": "casual",
                "quality": "photorealistic",
                "lighting": "studio lighting",
                "mood": "happy",
            },
        )
        assert "studio lighting" in result


# ─────────────────────────────────────────────────────────────────────────────
# generate_style_variations
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateStyleVariations:
    def test_each_style_becomes_variation(self):
        spt = _make_spt()
        styles = ["watercolor", "oil painting", "sketch"]
        result = spt.generate_style_variations("a cat", styles)
        assert result == [
            "a cat, watercolor style",
            "a cat, oil painting style",
            "a cat, sketch style",
        ]

    def test_empty_styles_returns_empty_list(self):
        spt = _make_spt()
        assert spt.generate_style_variations("base prompt", []) == []

    def test_single_style(self):
        spt = _make_spt()
        result = spt.generate_style_variations("portrait", ["baroque"])
        assert len(result) == 1
        assert "baroque style" in result[0]


# ─────────────────────────────────────────────────────────────────────────────
# generate_quality_variations
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateQualityVariations:
    def test_quality_appended_to_base(self):
        spt = _make_spt()
        result = spt.generate_quality_variations("a mountain", ["4K", "8K"])
        assert "a mountain, 4K" in result
        assert "a mountain, 8K" in result

    def test_empty_qualities_returns_empty(self):
        spt = _make_spt()
        assert spt.generate_quality_variations("base", []) == []


# ─────────────────────────────────────────────────────────────────────────────
# analyze_prompt_performance
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzePromptPerformance:
    def test_empty_history_returns_zeros(self):
        spt = _make_spt()
        result = spt.analyze_prompt_performance()
        assert result["total"] == 0
        assert result["success_rate"] == 0
        assert result["categories"] == {}

    def test_all_successful(self):
        spt = _make_spt()
        spt.history = [
            {"category": "anime", "success": True},
            {"category": "anime", "success": True},
        ]
        result = spt.analyze_prompt_performance()
        assert result["total"] == 2
        assert result["success_rate"] == 100.0

    def test_partial_success_rate(self):
        spt = _make_spt()
        spt.history = [
            {"category": "anime", "success": True},
            {"category": "anime", "success": False},
            {"category": "anime", "success": True},
            {"category": "anime", "success": True},
        ]
        result = spt.analyze_prompt_performance()
        assert result["success_rate"] == 75.0

    def test_category_breakdown(self):
        spt = _make_spt()
        spt.history = [
            {"category": "anime", "success": True},
            {"category": "realistic", "success": False},
            {"category": "anime", "success": False},
        ]
        result = spt.analyze_prompt_performance()
        assert "anime" in result["categories"]
        assert "realistic" in result["categories"]
        assert result["categories"]["anime"]["total"] == 2
        assert result["categories"]["realistic"]["total"] == 1
        assert result["categories"]["anime"]["success_rate"] == 50.0

    def test_category_with_all_failed(self):
        spt = _make_spt()
        spt.history = [
            {"category": "fantasy", "success": False},
            {"category": "fantasy", "success": False},
        ]
        result = spt.analyze_prompt_performance()
        assert result["categories"]["fantasy"]["success_rate"] == 0.0
