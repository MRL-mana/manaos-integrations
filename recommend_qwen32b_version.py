#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qwen2.5-Coder-32B-Instructの推奨量子化バージョンを表示"""

import sys
import requests
import os

try:
    from manaos_integrations._paths import LM_STUDIO_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import LM_STUDIO_PORT  # type: ignore
    except Exception:  # pragma: no cover
        LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))


DEFAULT_LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", f"http://127.0.0.1:{LM_STUDIO_PORT}")

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("Qwen2.5-Coder-32B-Instruct 量子化バージョン推奨")
print("=" * 60)

# 量子化バージョンの比較
quantization_versions = {
    "Q4_K_M": {
        "size": "約18GB",
        "precision": "中",
        "recommendation": "メモリ制約がある場合",
        "score": 3
    },
    "Q5_K_M": {
        "size": "約22GB",
        "precision": "高",
        "recommendation": "⭐ 推奨（バランス良好）",
        "score": 5
    },
    "Q6_K": {
        "size": "約25GB",
        "precision": "高",
        "recommendation": "より高い精度が必要な場合",
        "score": 4
    },
    "Q8_0": {
        "size": "約32GB",
        "precision": "最高",
        "recommendation": "最高精度が必要な場合",
        "score": 3
    }
}

print("\n量子化バージョン比較:")
print("-" * 60)
for version, info in quantization_versions.items():
    print(f"\n【{version}】")
    print(f"  サイズ: {info['size']}")
    print(f"  精度: {info['precision']}")
    print(f"  推奨: {info['recommendation']}")

print("\n" + "=" * 60)
print("推奨: Q5_K_M ⭐")
print("=" * 60)
print("\n理由:")
print("  ✓ 精度とサイズのバランスが最適")
print("  ✓ OCR修正タスクに十分な精度")
print("  ✓ 16GB VRAMで動作可能")
print("  ✓ 処理速度も良好")

print("\nダウンロード方法:")
print("  1. LM Studioを起動")
print("  2. 「Search」タブを開く")
print("  3. \"qwen2.5-coder-32b-instruct\" を検索")
print("  4. 「Q5_K_M」バージョンを選択")
print("  5. 「Download」をクリック")

# 現在のモデルを確認
try:
    r = requests.get(f"{DEFAULT_LM_STUDIO_URL}/v1/models", timeout=5)
    if r.status_code == 200:
        models_data = r.json().get('data', [])
        available_models = [model.get('id', '') for model in models_data]
        
        qwen32b_models = [m for m in available_models if 'qwen2.5-coder-32b' in m.lower()]
        
        if qwen32b_models:
            print("\n" + "=" * 60)
            print("現在ダウンロード済みの32Bモデル:")
            print("=" * 60)
            for model in qwen32b_models:
                print(f"  ✓ {model}")
        else:
            print("\n現在、32Bモデルはダウンロードされていません")
except Exception:
    pass

print("\n" + "=" * 60)
