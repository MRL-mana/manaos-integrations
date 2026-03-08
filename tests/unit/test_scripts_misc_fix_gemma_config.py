"""
Unit tests for scripts/misc/fix_gemma_config.py
（ComfyUI Gemma config.json 修正スクリプト）
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# manaos_logger は存在しない場合があるためモック
sys.modules.setdefault("manaos_logger", MagicMock())

from scripts.misc.fix_gemma_config import fix_config_json, GEMMA3_TEXT_CONFIG


class TestFixConfigJson:
    def test_creates_new_config_when_missing(self, tmp_path: Path):
        """config.json が存在しない場合は新規作成"""
        cfg = tmp_path / "config.json"
        result = fix_config_json(cfg)
        assert result is True
        assert cfg.exists()
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["model_type"] == "gemma3_text"

    def test_adds_model_type_to_existing_config(self, tmp_path: Path):
        """既存の config.json に model_type がなければ追加"""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"hidden_size": 3072}), encoding="utf-8")
        result = fix_config_json(cfg)
        assert result is True
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["model_type"] == "gemma3_text"
        # 既存キーは保持
        assert data["hidden_size"] == 3072

    def test_skips_if_model_type_already_present(self, tmp_path: Path):
        """既に model_type があれば True を返して変更しない"""
        existing = {"model_type": "custom_type", "hidden_size": 1}
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(existing), encoding="utf-8")
        result = fix_config_json(cfg)
        assert result is True
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["model_type"] == "custom_type"  # 変更されていない

    def test_returns_false_on_invalid_json(self, tmp_path: Path):
        """壊れた JSON に対して False を返す"""
        cfg = tmp_path / "config.json"
        cfg.write_text("NOT JSON", encoding="utf-8")
        result = fix_config_json(cfg)
        assert result is False

    def test_new_config_has_required_keys(self, tmp_path: Path):
        """新規作成される config.json は必要なキーを全て持つ"""
        cfg = tmp_path / "config.json"
        fix_config_json(cfg)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        for key in ("model_type", "architectures", "vocab_size", "hidden_size"):
            assert key in data


class TestGemma3TextConfig:
    def test_model_type_is_gemma3_text(self):
        assert GEMMA3_TEXT_CONFIG["model_type"] == "gemma3_text"

    def test_architectures_includes_gemma_model(self):
        assert "Gemma3ForCausalLM" in GEMMA3_TEXT_CONFIG["architectures"]
