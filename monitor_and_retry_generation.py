#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像生成を監視し、エラー時は再試行"""

import requests
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
GALLERY_API = "http://localhost:5559/api/generate"

print("=" * 60)
print("画像生成監視と自動再試行")
print("=" * 60)
print()

# 最新のprompt_idを確認
print("最新の履歴を確認中...")
try:
    response = requests.get(f"{COMFYUI_URL}/history", timeout=10)
    if response.status_code == 200:
        history = response.json()
        if history:
            # 最新の5件を確認
            items = list(history.items())[-5:]
            print(f"最新5件の履歴:")
            for prompt_id, data in items:
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                outputs = data.get("outputs", {})
                has_images = any("images" in node_output for node_output in outputs.values())
                
                print(f"  Prompt ID: {prompt_id[:20]}...")
                print(f"    ステータス: {status_str}")
                print(f"    画像あり: {has_images}")
                
                if status_str == "error":
                    messages = status.get("messages", [])
                    for msg in messages:
                        if msg[0] == "execution_error":
                            error_data = msg[1]
                            print(f"    エラー: {error_data.get('exception_message', 'N/A')[:50]}")
                print()
except Exception as e:
    print(f"履歴確認エラー: {e}")

print()
print("-" * 60)
print()

# 新しい画像生成を試行
print("新しい画像生成を試行中...")
payload = {
    "prompt": "Japanese, beautiful woman, high quality, masterpiece, best quality",
    "model": "realisian_v60.safetensors",
    "steps": 30,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 768,
    "sampler": "euler",  # dpmpp_2mの代わりにeulerを試す
    "scheduler": "normal",  # karrasの代わりにnormalを試す
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
            print(f"[OK] ジョブ送信成功！")
            print(f"   ジョブID: {job_id}")
            print(f"   プロンプトID: {prompt_id}")
            print()
            print("   画像生成を監視中...（最大120秒）")
            
            # 生成完了を待つ
            success = False
            for i in range(60):
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
                                    print(f"   [OK] 画像生成完了！")
                                    for node_id, node_output in outputs.items():
                                        if "images" in node_output:
                                            images = node_output["images"]
                                            for img in images:
                                                print(f"   ファイル名: {img.get('filename', 'N/A')}")
                                    success = True
                                    break
                            elif status_str == "error":
                                print(f"   [ERROR] エラーが発生しました")
                                messages = status.get("messages", [])
                                for msg in messages:
                                    if msg[0] == "execution_error":
                                        error_data = msg[1]
                                        error_msg = error_data.get('exception_message', 'N/A')
                                        print(f"   エラー: {error_msg}")
                                        
                                        # エンコーディングエラーの場合
                                        if "Invalid argument" in error_msg or "Errno 22" in error_msg:
                                            print()
                                            print("   [重要] ComfyUIのエンコーディングエラーが発生しています。")
                                            print("   ComfyUIを再起動してください:")
                                            print("     1. ComfyUIを停止（Ctrl+C）")
                                            print("     2. 以下のコマンドで再起動:")
                                            print("        powershell -ExecutionPolicy Bypass -File start_comfyui_fixed.ps1")
                                break
                except:
                    pass
                
                if i % 10 == 0 and i > 0:
                    print(f"   待機中... ({i*2}秒経過)")
            
            if not success:
                print()
                print("   [警告] タイムアウトしました。ComfyUIの状態を確認してください。")
        else:
            print(f"[ERROR] エラー: {result.get('error')}")
    else:
        print(f"[ERROR] HTTPエラー: {response.status_code}")
        print(f"   レスポンス: {response.text[:200]}")
        
except Exception as e:
    print(f"[ERROR] 例外エラー: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("完了")
print("=" * 60)
