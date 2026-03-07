"""
Unit tests for scripts/misc/mufufu_config.py
Pure-config module — no mocking needed.
"""
import pytest
from scripts.misc.mufufu_config import (
    MUFUFU_NEGATIVE_PROMPT,
    ANATOMY_POSITIVE_TAGS,
    QUALITY_TAGS,
    OPTIMIZED_PARAMS,
    PROMPT_TEMPLATES,
    PROMPT_ORDER,
    RECOMMENDED_MODEL_LORA_PAIRS,
    build_ordered_prompt,
    build_mufufu_prompt,
    get_default_negative_prompt_safe,
    get_optimized_params,
)


# ── TestConstants ─────────────────────────────────────────────────────────────
class TestConstants:
    def test_negative_prompt_is_string(self):
        assert isinstance(MUFUFU_NEGATIVE_PROMPT, str)
        assert len(MUFUFU_NEGATIVE_PROMPT) > 0

    def test_negative_prompt_contains_bad_anatomy(self):
        assert "bad anatomy" in MUFUFU_NEGATIVE_PROMPT

    def test_anatomy_positive_tags_is_string(self):
        assert isinstance(ANATOMY_POSITIVE_TAGS, str)
        assert "anatomy" in ANATOMY_POSITIVE_TAGS

    def test_quality_tags_is_string(self):
        assert isinstance(QUALITY_TAGS, str)
        assert "masterpiece" in QUALITY_TAGS

    def test_optimized_params_has_required_keys(self):
        for key in ["steps", "guidance_scale", "sampler", "scheduler",
                    "min_width", "min_height"]:
            assert key in OPTIMIZED_PARAMS

    def test_optimized_params_steps_gt_30(self):
        # 30以下だと身体崩れが増える
        assert OPTIMIZED_PARAMS["steps"] > 30

    def test_prompt_order_is_list(self):
        assert isinstance(PROMPT_ORDER, list)
        assert len(PROMPT_ORDER) > 0

    def test_recommended_model_lora_pairs_is_dict(self):
        assert isinstance(RECOMMENDED_MODEL_LORA_PAIRS, dict)

    def test_prompt_templates_has_default_and_mufufu(self):
        assert "default" in PROMPT_TEMPLATES
        assert "mufufu" in PROMPT_TEMPLATES


# ── TestBuildOrderedPrompt ─────────────────────────────────────────────────────
class TestBuildOrderedPrompt:
    def test_basic_sections_ordered(self):
        sections = {
            "quality": "masterpiece, 8k",
            "character": "1girl, Japanese woman",
        }
        result = build_ordered_prompt(sections)
        # quality comes before character in PROMPT_ORDER
        assert "masterpiece, 8k" in result
        assert "1girl, Japanese woman" in result
        qi = result.index("masterpiece")
        ci = result.index("1girl")
        assert qi < ci

    def test_missing_sections_skipped(self):
        result = build_ordered_prompt({"quality": "best quality"})
        assert result == "best quality"

    def test_empty_sections_returns_empty_string(self):
        assert build_ordered_prompt({}) == ""

    def test_list_value_joined_with_comma(self):
        result = build_ordered_prompt({"quality": ["masterpiece", "8k"]})
        assert "masterpiece" in result
        assert "8k" in result

    def test_none_value_skipped(self):
        result = build_ordered_prompt({"quality": None, "character": "1girl"})
        assert result == "1girl"

    def test_empty_string_value_skipped(self):
        result = build_ordered_prompt({"quality": "", "character": "1girl"})
        assert result == "1girl"

    def test_all_sections_present(self):
        sections = {k: k + "_value" for k in PROMPT_ORDER}
        result = build_ordered_prompt(sections)
        for key in PROMPT_ORDER:
            assert key + "_value" in result

    def test_ordering_respects_prompt_order(self):
        # anatomy should come before quality
        assert PROMPT_ORDER.index("anatomy") < PROMPT_ORDER.index("quality")
        sections = {"anatomy": "correct anatomy", "quality": "masterpiece"}
        result = build_ordered_prompt(sections)
        assert result.index("correct anatomy") < result.index("masterpiece")


# ── TestBuildMufufuPrompt ──────────────────────────────────────────────────────
class TestBuildMufufuPrompt:
    def test_includes_character_tags(self):
        result = build_mufufu_prompt("1girl, blonde hair")
        assert "1girl, blonde hair" in result

    def test_includes_quality_tags(self):
        result = build_mufufu_prompt("1girl")
        assert "masterpiece" in result

    def test_includes_mischievous_expression(self):
        result = build_mufufu_prompt("1girl")
        assert "mischievous expression" in result

    def test_anatomy_tags_included_by_default(self):
        result = build_mufufu_prompt("1girl")
        assert "anatomy" in result

    def test_anatomy_tags_excluded_when_false(self):
        result = build_mufufu_prompt("1girl", include_anatomy_tags=False)
        # ANATOMY_POSITIVE_TAGS not present
        assert ANATOMY_POSITIVE_TAGS not in result

    def test_situation_included(self):
        result = build_mufufu_prompt("1girl", situation="at the beach")
        assert "at the beach" in result

    def test_action_included(self):
        result = build_mufufu_prompt("1girl", action="waving hand")
        assert "waving hand" in result

    def test_empty_situation_not_added(self):
        result_with = build_mufufu_prompt("1girl", situation="beach")
        result_without = build_mufufu_prompt("1girl")
        assert "beach" not in result_without
        assert "beach" in result_with

    def test_returns_string(self):
        assert isinstance(build_mufufu_prompt("1girl"), str)


# ── TestGetDefaultNegativePromptSafe ──────────────────────────────────────────
class TestGetDefaultNegativePromptSafe:
    def test_returns_string(self):
        result = get_default_negative_prompt_safe()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_underage_filter(self):
        result = get_default_negative_prompt_safe()
        assert "underage" in result or "child" in result

    def test_contains_explicit_filter(self):
        result = get_default_negative_prompt_safe()
        assert "nude" in result


# ── TestGetOptimizedParams ────────────────────────────────────────────────────
class TestGetOptimizedParams:
    def test_returns_dict(self):
        assert isinstance(get_optimized_params(), dict)

    def test_default_steps(self):
        params = get_optimized_params()
        assert params["steps"] == OPTIMIZED_PARAMS["steps"]

    def test_override_steps(self):
        params = get_optimized_params(steps=60)
        assert params["steps"] == 60

    def test_original_not_mutated(self):
        get_optimized_params(steps=9999)
        assert OPTIMIZED_PARAMS["steps"] != 9999

    def test_multiple_overrides(self):
        params = get_optimized_params(steps=40, guidance_scale=9.0)
        assert params["steps"] == 40
        assert params["guidance_scale"] == 9.0
        # unrelated keys remain
        assert "sampler" in params
