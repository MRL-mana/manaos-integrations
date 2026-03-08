"""Tests for scripts/misc/download_missing_loras_models.py"""
import importlib
import sys

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "download_missing_loras_models" in sys.modules:
        return sys.modules["download_missing_loras_models"]
    return importlib.import_module("download_missing_loras_models")


class TestSearchAndDownload:
    def test_returns_none_when_civitai_unavailable(self, _mod, monkeypatch):
        """CIVITAI_AVAILABLE=False のとき即座に None を返す"""
        monkeypatch.setattr(_mod, "CIVITAI_AVAILABLE", False)
        result = _mod.search_and_download("lora query")
        assert result is None

    def test_accepts_model_type_parameter(self, _mod, monkeypatch):
        """model_type 引数を受け取れること"""
        monkeypatch.setattr(_mod, "CIVITAI_AVAILABLE", False)
        result = _mod.search_and_download("query", model_type="Checkpoint")
        assert result is None

    def test_accepts_download_dir_parameter(self, _mod, monkeypatch, tmp_path):
        """download_dir 引数を受け取れること"""
        monkeypatch.setattr(_mod, "CIVITAI_AVAILABLE", False)
        result = _mod.search_and_download("query", download_dir=tmp_path)
        assert result is None
