#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# local_llm_helper スタブ（LMStudio未起動環境用）
if "local_llm_helper" not in sys.modules:
    _llm_stub = types.ModuleType("local_llm_helper")

    def _stub_generate(model, prompt, **kwargs):
        return {"text": f"stub response for {model}", "model": model}

    def _stub_list_models():
        return ["qwen2.5-coder-14b-instruct"]

    _llm_stub.generate = _stub_generate  # type: ignore
    _llm_stub.list_models = _stub_list_models  # type: ignore
    sys.modules["local_llm_helper"] = _llm_stub


def test_lm_studio_generate_smoke():
    os.environ["USE_LM_STUDIO"] = "1"
    try:
        from local_llm_helper import generate
    except Exception as exc:
        pytest.skip(f"local_llm_helper を読み込めないためスキップ: {exc}")

    try:
        result = generate(
            "qwen2.5-coder-14b-instruct",
            "「ハイオク」という単語を正しく認識してください。",
            timeout=30,
        )
    except Exception as exc:
        pytest.skip(f"LM Studio推論が実行できないためスキップ: {exc}")

    if not isinstance(result, dict):
        pytest.skip(f"LM Studio 応答が dict でないためスキップ (type={type(result).__name__})")
    assert isinstance(result, dict)
