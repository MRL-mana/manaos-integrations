#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioの各モデルをテスト"""

import sys
import requests
import time

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

print("=" * 60)
print("LM Studio モデルテスト")
print("=" * 60)

# 利用可能なモデルを取得
try:
    r = requests.get('http://127.0.0.1:1234/v1/models', timeout=5)
    if r.status_code == 200:
        models_data = r.json().get('data', [])
        available_models = [model.get('id', '') for model in models_data]
        
        print(f"\n利用可能なモデル: {len(available_models)}個")
        
        # 各モデルをテスト
        test_prompt = "「ハイオク」という単語を正しく認識してください。"
        
        for model_name in available_models[:5]:  # 最初の5モデルをテスト
            print(f"\n【テスト】{model_name}")
            try:
                url = "http://127.0.0.1:1234/v1/chat/completions"
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": test_prompt}],
                    "temperature": 0.7
                }
                
                start = time.time()
                response = requests.post(url, json=data, timeout=30)
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    print(f"  ✓ 成功 ({elapsed:.1f}秒)")
                    print(f"  応答: {content[:50]}...")
                else:
                    print(f"  ✗ エラー: HTTP {response.status_code}")
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get('error', {}).get('message', '')[:100]
                    if error_msg:
                        print(f"  詳細: {error_msg}")
            except Exception as e:
                print(f"  ✗ エラー: {e}")
    else:
        print(f"✗ LM Studio APIエラー: HTTP {r.status_code}")
except Exception as e:
    print(f"✗ エラー: {e}")

print("\n" + "=" * 60)
