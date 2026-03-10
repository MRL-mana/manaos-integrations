"""Unit tests for tools/trinity_universal_model_switcher.py — _classify_model."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

# torch / psutil が未インストールの場合にスタブを注入
if "torch" not in sys.modules:
    sys.modules["torch"] = MagicMock()
if "psutil" not in sys.modules:
    sys.modules.setdefault("psutil", MagicMock())

# __init__ の副作用（mkdir / scan/psutil）を避けてクラスだけロード
import trinity_universal_model_switcher as ums_mod
UniversalModelSwitcher = ums_mod.UniversalModelSwitcher


def _make_switcher() -> UniversalModelSwitcher:  # type: ignore[valid-type]
    """__init__ をスキップして純粋メソッドだけテストするヘルパー。"""
    with patch.object(UniversalModelSwitcher, "__init__", lambda self: None):
        s = UniversalModelSwitcher()
    return s


class TestClassifyModel:
    def test_wan_keyword_in_filename(self):
        s = _make_switcher()
        assert s._classify_model("wan_anime_v3.safetensors", {}) == "wan_2_2"

    def test_anime_keyword_in_filename(self):
        s = _make_switcher()
        assert s._classify_model("anime_style.safetensors", {}) == "wan_2_2"

    def test_waifu_keyword_in_filename(self):
        s = _make_switcher()
        assert s._classify_model("waifu_diffusion.safetensors", {}) == "wan_2_2"

    def test_majicmix_keyword(self):
        s = _make_switcher()
        assert s._classify_model("majicmix_v7.safetensors", {}) == "wan_2_2"

    def test_sdxl_keyword_in_filename(self):
        s = _make_switcher()
        assert s._classify_model("dreamshaper_sdxl.safetensors", {}) == "sdxl"

    def test_xl_keyword_in_filename(self):
        s = _make_switcher()
        assert s._classify_model("photoreal_xl.safetensors", {}) == "sdxl"

    def test_realistic_keyword(self):
        s = _make_switcher()
        assert s._classify_model("realistic_vision.safetensors", {}) == "sdxl"

    def test_fast_keyword(self):
        s = _make_switcher()
        assert s._classify_model("fast_inference.safetensors", {}) == "fast"

    def test_lora_keyword(self):
        s = _make_switcher()
        assert s._classify_model("character_lora.safetensors", {}) == "fast"

    def test_tiny_keyword(self):
        s = _make_switcher()
        assert s._classify_model("tiny_model.safetensors", {}) == "fast"

    def test_unknown_filename_returns_unknown(self):
        s = _make_switcher()
        assert s._classify_model("mystery_v1.safetensors", {}) == "unknown"

    def test_info_name_takes_priority_wan(self):
        s = _make_switcher()
        # ファイル名は無関係だが info.name に "anime" → wan_2_2
        result = s._classify_model("plainfile.safetensors", {"name": "AnimeModel"})
        assert result == "wan_2_2"

    def test_info_name_sdxl(self):
        s = _make_switcher()
        result = s._classify_model("plainfile.safetensors", {"name": "realisticVision"})
        assert result == "sdxl"

    def test_case_insensitive_filename(self):
        s = _make_switcher()
        # filename は lower で比較するので大文字でも OK
        assert s._classify_model("WAN_Model.safetensors", {}) == "wan_2_2"
