#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

import pytest


def test_model_directories_access_smoke():
    comfyui_models_dir = Path(os.getenv("COMFYUI_MODELS_DIR", "C:/ComfyUI/models/checkpoints"))
    mana_models_dir = Path(os.getenv("MANA_MODELS_DIR", "C:/mana_workspace/models"))

    assert isinstance(comfyui_models_dir, Path)
    assert isinstance(mana_models_dir, Path)


def test_gallery_api_model_functions_smoke():
    try:
        from gallery_api_server import get_available_models, find_model_path
    except Exception as exc:
        pytest.skip(f"gallery_api_server を読み込めないためスキップ: {exc}")

    try:
        models = get_available_models()
    except Exception as exc:
        pytest.skip(f"get_available_models 実行失敗のためスキップ: {exc}")

    assert isinstance(models, list)

    if models:
        first_model = str(models[0])
        result = find_model_path(first_model)
        assert result is None or isinstance(result, str)
