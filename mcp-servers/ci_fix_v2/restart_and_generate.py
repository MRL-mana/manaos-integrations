#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI再起動後、画像生成を実行"""

import requests
import time
import sys
import io
import os

from _paths import COMFYUI_PORT, GALLERY_PORT

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
GALLERY_API = os.getenv("GALLERY_GENERATE_API", f"http://127.0.0.1:{GALLERY_PORT}/api/generate")

print("=" * 60)
print("ComfyUI接続確認と画像生成")
print("=" * 60)
print()

# 1. ComfyUIの接続確認
print("1. ComfyUIの接続を確認中...")
try:
    response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
    if response.status_code == 200:
        print("   ✅ ComfyUI接続OK")
    else:
        print(f"   ⚠️ ComfyUI接続エラー: {response.status_code}")
        print("   ComfyUIが起動していない可能性があります。")
        print("   start_comfyui_fixed.ps1 でComfyUIを起動してください。")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ComfyUI接続失敗: {e}")
    print("   ComfyUIが起動していない可能性があります。")
    print("   start_comfyui_fixed.ps1 でComfyUIを起動してください。")
    sys.exit(1)

print()

# 2. キューを確認
print("2. ComfyUIキューを確認中...")
try:
    response = requests.get(f"{COMFYUI_URL}/queue", timeout=5)
    if response.status_code == 200:
        data = response.json()
        queue_running = len(data.get("queue_running", []))
        queue_pending = len(data.get("queue_pending", []))
        print(f"   実行中: {queue_running}件")
        print(f"   待機中: {queue_pending}件")
except Exception as e:
    print(f"   ⚠️ キュー確認エラー: {e}")

print()

# 3. テスト画像生成
print("3. テスト画像生成を実行中...")
payload = {
    "prompt": "Japanese, beautiful woman, high quality, masterpiece",
    "model": "realisian_v60.safetensors",
    "steps": 25,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 768,
    "sampler": "dpmpp_2m",
    "scheduler": "karras",
    "mufufu_mode": False
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
            prompt_id = result.get("prompt_id")
            print(f"   ✅ ジョブ送信成功！")
            print(f"   ジョブID: {job_id}")
            print(f"   プロンプトID: {prompt_id}")
            print()
            print("   画像生成を監視中...（最大60秒）")
            
            # 生成完了を待つ
            for i in range(30):
                time.sleep(2)
                try:
                    history_response = requests.get(
                        f"{COMFYUI_URL}/history/{prompt_id}",
                        timeout=5
                    )
                    if history_response.status_code == 200:
                        history = history_response.json()
                        if prompt_id in history:
                            data = history[prompt_id]
                            status = data.get("status", {})
                            status_str = status.get("status_str", "unknown")
                            
                            if status_str == "success":
                                outputs = data.get("outputs", {})
                                if outputs:
                                    print(f"   ✅ 画像生成完了！")
                                    for node_id, node_output in outputs.items():
                                        if "images" in node_output:
                                            images = node_output["images"]
                                            for img in images:
                                                print(f"   ファイル名: {img.get('filename', 'N/A')}")
                                    break
                            elif status_str == "error":
                                print(f"   ❌ エラーが発生しました")
                                messages = status.get("messages", [])
                                for msg in messages:
                                    if msg[0] == "execution_error":
                                        error_data = msg[1]
                                        print(f"   エラー: {error_data.get('exception_message', 'N/A')}")
                                break
                except Exception:
                    pass
                
                if i % 5 == 0:
                    print(f"   待機中... ({i*2}秒経過)")
        else:
            print(f"   ❌ エラー: {result.get('error')}")
    else:
        print(f"   ❌ HTTPエラー: {response.status_code}")
        print(f"   レスポンス: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ 例外エラー: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("完了")
print("=" * 60)
