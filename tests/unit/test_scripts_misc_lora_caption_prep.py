"""
Unit tests for scripts/misc/lora_caption_prep.py
"""
import base64
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.misc.lora_caption_prep import (
    IMAGE_EXTS,
    _clean_caption,
    _list_vision_models,
    _pick_default_vision_model,
    _read_b64,
)


class TestImageExts:
    def test_contains_png(self):
        assert ".png" in IMAGE_EXTS

    def test_contains_jpg(self):
        assert ".jpg" in IMAGE_EXTS

    def test_contains_webp(self):
        assert ".webp" in IMAGE_EXTS


class TestPickDefaultVisionModel:
    def test_prefers_qwen(self):
        models = ["llava:7b", "qwen2.5-vl:7b", "moondream:1b"]
        result = _pick_default_vision_model(models)
        assert result is not None and "qwen" in result.lower()

    def test_prefers_llava_over_moondream(self):
        models = ["moondream:1b", "llava:7b"]
        result = _pick_default_vision_model(models)
        assert result is not None and "llava" in result.lower()

    def test_returns_first_if_no_known_model(self):
        models = ["unknownvision:13b", "another:7b"]
        result = _pick_default_vision_model(models)
        assert result == models[0]

    def test_returns_none_when_empty(self):
        result = _pick_default_vision_model([])
        assert result is None


class TestCleanCaption:
    def test_strips_whitespace(self):
        assert _clean_caption("  hello  ") == "hello"

    def test_removes_markdown_code_block(self):
        result = _clean_caption("```\nsome caption\n```")
        assert "```" not in result

    def test_plain_text_unchanged(self):
        text = "a cat sitting on a mat"
        assert _clean_caption(text) == text


class TestListVisionModels:
    def test_returns_model_names_on_success(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "models": [{"name": "llava:7b"}, {"name": "qwen2.5-vl:3b"}]
        }
        fake_response.raise_for_status = MagicMock()
        with patch("scripts.misc.lora_caption_prep.requests.get", return_value=fake_response):
            result = _list_vision_models("http://localhost:11434")
        assert "llava:7b" in result
        assert "qwen2.5-vl:3b" in result

    def test_returns_empty_list_on_exception(self):
        with patch(
            "scripts.misc.lora_caption_prep.requests.get",
            side_effect=Exception("connection error"),
        ):
            result = _list_vision_models("http://localhost:11434")
        assert result == []


class TestReadB64:
    def test_encodes_file_correctly(self, tmp_path: Path):
        content = b"hello binary"
        p = tmp_path / "img.bin"
        p.write_bytes(content)
        result = _read_b64(p)
        decoded = base64.b64decode(result)
        assert decoded == content

    def test_returns_string(self, tmp_path: Path):
        p = tmp_path / "data.bin"
        p.write_bytes(b"\x00\x01\x02")
        assert isinstance(_read_b64(p), str)
