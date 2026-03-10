#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioを簡単にテスト"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# 環境変数を設定
os.environ['USE_LM_STUDIO'] = '1'

from local_llm_helper import generate, list_models

print("=" * 60)
print("LM Studio 簡単テスト")
print("=" * 60)

# 1. 利用可能なモデルを確認
print("\n【1】利用可能なモデル:")
try:
    models = list_models()
    print(f"  モデル数: {len(models)}")
    for model in models[:5]:
        print(f"  - {model}")
except Exception as e:
    print(f"  ✗ エラー: {e}")

# 2. 簡単な推論テスト
print("\n【2】推論テスト:")
test_models = [
    "qwen2.5-coder-7b-instruct",  # 小さいモデルから試す
    "qwen2.5-coder-14b-instruct",
    "qwen2.5-coder-32b-instruct",
]

for model_name in test_models:
    print(f"\n  テスト: {model_name}")
    try:
        result = generate(
            model=model_name,
            prompt="「ハイオク」という単語を正しく認識してください。",
            timeout=30
        )
        
        if result and result.get('response'):
            print(f"    ✓ 成功！")
            print(f"    応答: {result['response'][:100]}...")
            print(f"    ソース: {result.get('source', 'unknown')}")
            break  # 最初に成功したモデルで終了
        elif result and result.get('error'):
            print(f"    ✗ エラー: {result.get('error')}")
            print(f"    メッセージ: {result.get('message', '')[:100]}")
    except Exception as e:
        print(f"    ✗ 例外: {e}")

print("\n" + "=" * 60)
