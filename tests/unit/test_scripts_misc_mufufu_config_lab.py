"""
Unit tests for scripts/misc/mufufu_config_lab.py
"""
import sys
import types

# ─── mufufu_config stub (import guard) ────────────────────────────────────────
if "mufufu_config" not in sys.modules:
    _mc_mod = types.ModuleType("mufufu_config")
    _mc_mod.ANATOMY_POSITIVE_TAGS = "perfect anatomy"  # type: ignore
    _mc_mod.QUALITY_TAGS = "masterpiece"  # type: ignore
    _mc_mod.OPTIMIZED_PARAMS = {"steps": 50}  # type: ignore
    _mc_mod.RECOMMENDED_MODEL_LORA_PAIRS = {}  # type: ignore
    _mc_mod.build_ordered_prompt = lambda sections: ""  # type: ignore
    _mc_mod.build_mufufu_prompt = lambda *a, **kw: ""  # type: ignore
    _mc_mod.get_optimized_params = lambda **kw: {}  # type: ignore
    _mc_mod.PROMPT_ORDER = []  # type: ignore
    _mc_mod.PROMPT_TEMPLATES = {}  # type: ignore
    sys.modules["mufufu_config"] = _mc_mod

from scripts.misc.mufufu_config_lab import (
    LAB_NEGATIVE_PROMPT,
    get_default_negative_prompt_safe,
)


class TestLabNegativePrompt:
    def test_is_non_empty_string(self):
        assert isinstance(LAB_NEGATIVE_PROMPT, str) and LAB_NEGATIVE_PROMPT.strip()

    def test_contains_bad_anatomy(self):
        assert "bad anatomy" in LAB_NEGATIVE_PROMPT

    def test_contains_bad_hands(self):
        assert "bad hands" in LAB_NEGATIVE_PROMPT

    def test_does_not_contain_nsfw_suppression(self):
        # lab mode deliberately avoids nsfw-suppression tags
        nsfw_tags = ["nsfw", "nude", "naked", "explicit"]
        for tag in nsfw_tags:
            assert tag not in LAB_NEGATIVE_PROMPT.lower()


class TestGetDefaultNegativePromptSafe:
    def test_returns_empty_string(self):
        result = get_default_negative_prompt_safe()
        assert result == ""

    def test_return_type_is_str(self):
        assert isinstance(get_default_negative_prompt_safe(), str)
