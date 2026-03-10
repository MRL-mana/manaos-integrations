#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""プロンプトが正しく反映されるかテスト"""

import requests
import time
import sys
import io
import os

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

from _paths import GALLERY_PORT

GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/generate"

# テスト用の明確なプロンプト
test_prompt = "clear and pure gyaru style, naked, big eyes, beautiful face, toned body, sexual act, in bedroom, high quality"

print("=" * 60)
print("プロンプトテスト: 明確なプロンプトで画像を生成")
print("=" * 60)
print()
print(f"【送信するプロンプト】")
print(test_prompt)
print()

data = {
    "prompt": test_prompt,
    "model": "realisian_v60.safetensors",
    "steps": 50,
    "guidance_scale": 7.5,
    "width": 768,
    "height": 1024,
    "sampler": "dpmpp_2m",
    "scheduler": "karras",
    "negative_prompt": "bad anatomy, deformed, blurry",
    "seed": 12345,
    "mufufu_mode": True
}

try:
    print("画像生成を開始...")
    response = requests.post(GALLERY_API, json=data, timeout=30)

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            job_id = result.get("job_id")
            print(f"✓ ジョブID: {job_id}")
            print()
            print("画像生成を待機中...")
            print("（完了まで1-2分かかる場合があります）")
            print()

            # ジョブの完了を待つ
            for i in range(60):
                time.sleep(2)
                job_response = requests.get(f"http://127.0.0.1:5559/api/job/{job_id}")
                if job_response.status_code == 200:
                    job_data = job_response.json()
                    status = job_data.get("status")
                    print(f"ステータス: {status}")

                    if status == "completed":
                        filename = job_data.get("filename")
                        print(f"\n✓ 画像生成完了!")
                        print(f"ファイル名: {filename}")
                        print()

                        # メタデータを確認
                        if "metadata" in job_data:
                            metadata = job_data["metadata"]
                            print("【保存されたメタデータ】")
                            print(f"プロンプト: {metadata.get('prompt', 'N/A')}")
                            print(f"元のプロンプト: {metadata.get('original_prompt', 'N/A')}")
                            print(f"ネガティブプロンプト: {metadata.get('negative_prompt', 'N/A')}")
                            print(f"モデル: {metadata.get('model', 'N/A')}")
                            print(f"Seed: {metadata.get('seed', 'N/A')}")
                        else:
                            print("⚠ メタデータが見つかりません")

                        print()
                        print(f"画像URL: http://127.0.0.1:5559/images/{filename}")
                        break
                    elif status == "failed":
                        error = job_data.get("error", "Unknown error")
                        print(f"✗ エラー: {error}")
                        break
        else:
            print(f"✗ エラー: {result.get('error', 'Unknown error')}")
    else:
        print(f"✗ HTTP {response.status_code}: {response.text}")
except Exception as e:
    print(f"✗ エラー: {e}")
    import traceback
    traceback.print_exc()
