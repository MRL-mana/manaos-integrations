#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""10枚の画像を複数モデルで生成"""

import requests
import time
import json
import sys
import io

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/generate"

# 利用可能なモデル
models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosa25D_v12.safetensors",
    "speciosaRealistica_v12b.safetensors",
    "uwazumimixILL_v50.safetensors"
]

# プロンプト（日本人タグは自動追加される）
prompts = [
    "beautiful woman, elegant pose, high quality",
    "cute girl, smile, cheerful expression",
    "woman, traditional Japanese style, kimono",
    "beauty, modern fashion, stylish",
    "woman, casual style, natural",
    "girl, kawaii style, cute",
    "woman, professional, business",
    "beauty, artistic, creative",
    "woman, natural beauty, portrait",
    "girl, charming, lovely"
]

print("=" * 60)
print("10枚の画像を生成します（複数モデル使用）")
print("=" * 60)
print()

job_ids = []

for i in range(10):
    model = models[i % len(models)]
    prompt = prompts[i]

    print(f"[{i+1}/10] モデル: {model}")
    print(f"  プロンプト: {prompt}")

    payload = {
        "prompt": prompt,
        "model": model,
        "steps": 30,
        "guidance_scale": 7.5,
        "width": 768,
        "height": 1024,
        "sampler": "dpmpp_2m",
        "scheduler": "karras"
    }

    try:
        response = requests.post(
            GALLERY_API,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                job_ids.append(job_id)
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  × エラー: {result.get('error', 'Unknown error')}")
        else:
            print(f"  × HTTPエラー: {response.status_code}")
            print(f"    レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"  × 例外: {e}")

    # リクエスト間隔を空ける
    if i < 9:
        time.sleep(2)

print()
print("=" * 60)
print(f"[完了] {len(job_ids)}件の画像生成ジョブを送信しました")
print("=" * 60)
print()
print("ジョブID一覧:")
for i, job_id in enumerate(job_ids, 1):
    print(f"  {i}. {job_id}")
print()
print("画像生成の進行状況は以下で確認できます:")
print("  http://localhost:5559/api/job/<job_id>")
print()
print("生成された画像は以下で確認できます:")
print("  http://localhost:5559/api/images")
