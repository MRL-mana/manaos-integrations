"""Tests for scripts/misc/stable_diffusion_generator.py"""
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "stable_diffusion_generator" in sys.modules:
        return sys.modules["stable_diffusion_generator"]
    return importlib.import_module("stable_diffusion_generator")


def _make_instance(_mod):
    """__new__ でコンストラクタをスキップしてインスタンスを生成"""
    obj = _mod.StableDiffusionGenerator.__new__(_mod.StableDiffusionGenerator)
    obj.model_id = "test-model"
    obj.device = "cpu"
    obj.torch_dtype = None
    return obj


class TestStableDiffusionGeneratorInit:
    def test_raises_import_error_when_diffusers_unavailable(self, _mod, monkeypatch):
        """DIFFUSERS_AVAILABLE=False のとき ImportError が発生すること"""
        monkeypatch.setattr(_mod, "DIFFUSERS_AVAILABLE", False)
        with pytest.raises(ImportError):
            _mod.StableDiffusionGenerator()

    def test_raises_runtime_error_when_pipeline_load_fails(self, _mod, monkeypatch):
        """パイプラインのロードが失敗したとき RuntimeError が発生すること"""
        monkeypatch.setattr(_mod, "DIFFUSERS_AVAILABLE", True)
        mock_pipeline_cls = MagicMock(
            side_effect=RuntimeError("model download failed")
        )
        monkeypatch.setattr(_mod, "StableDiffusionPipeline", mock_pipeline_cls)
        with pytest.raises(RuntimeError):
            _mod.StableDiffusionGenerator(model_id="fake/model")


class TestUnload:
    def test_unload_deletes_pipeline_attribute(self, _mod):
        """unload() 後に pipeline 属性が削除されること"""
        obj = _make_instance(_mod)
        obj.pipeline = MagicMock()
        obj.unload()
        assert not hasattr(obj, "pipeline")

    def test_unload_noop_when_no_pipeline(self, _mod):
        """pipeline 属性がなくても unload() がエラーにならないこと"""
        obj = _make_instance(_mod)
        obj.unload()  # should not raise
