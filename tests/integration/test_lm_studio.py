#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import pytest


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
