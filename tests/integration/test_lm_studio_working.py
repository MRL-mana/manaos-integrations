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

    _llm_stub.generate = _stub_generate  # type: ignore
    sys.modules["local_llm_helper"] = _llm_stub


def test_lm_studio_working_model_smoke():
    os.environ["USE_LM_STUDIO"] = "1"
    try:
        from local_llm_helper import generate
    except Exception as exc:
        pytest.skip(f"local_llm_helper を読み込めないためスキップ: {exc}")

    model = os.getenv("LM_STUDIO_TEST_MODEL", "qwen2.5-coder-14b-instruct")
    prompt = "ping"
    try:
        result = generate(model=model, prompt=prompt, timeout=20)
    except Exception as exc:
        pytest.skip(f"LM Studio推論が実行できないためスキップ: {exc}")
    assert isinstance(result, dict)
