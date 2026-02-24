#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最終的な状態確認"""

import requests
import sys
import io
from datetime import datetime
import os

from _paths import COMFYUI_PORT, GALLERY_PORT

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
GALLERY_API = os.getenv("GALLERY_API", f"http://127.0.0.1:{GALLERY_PORT}/api").rstrip("/")

print("=" * 60)
print("最終状態確認")
print("=" * 60)
print()

# 1. ComfyUIキュー
print("1. ComfyUIキュー:")
try:
    response = requests.get(f"{COMFYUI_URL}/queue", timeout=5)
    if response.status_code == 200:
        data = response.json()
        queue_running = len(data.get("queue_running", []))
        queue_pending = len(data.get("queue_pending", []))
        print(f"   実行中: {queue_running}件")
        print(f"   待機中: {queue_pending}件")
        if queue_running == 0 and queue_pending == 0:
            print("   [注意] キューが空です。ジョブが処理されていない可能性があります。")
except Exception as e:
    print(f"   確認エラー: {e}")

print()

# 2. 最新の履歴（最新10件）
print("2. 最新の履歴（最新10件）:")
try:
    response = requests.get(f"{COMFYUI_URL}/history", timeout=5)
    if response.status_code == 200:
        history = response.json()
        if history:
            items = list(history.items())[-10:]
            success = 0
            error = 0
            for prompt_id, data in items:
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                outputs = data.get("outputs", {})
                has_images = any("images" in node_output for node_output in outputs.values())
                
                if status_str == "success" and has_images:
                    success += 1
                elif status_str == "error":
                    error += 1
                    messages = status.get("messages", [])
                    for msg in messages:
                        if msg[0] == "execution_error":
                            error_data = msg[1]
                            error_msg = error_data.get('exception_message', 'N/A')[:50]
                            print(f"   [ERROR] {prompt_id[:20]}... - {error_msg}")
                            break
            
            print(f"   成功: {success}件, エラー: {error}件")
        else:
            print("   履歴がありません")
except Exception as e:
    print(f"   確認エラー: {e}")

print()

# 3. 最新の画像
print("3. 最新の画像:")
try:
    response = requests.get(f"{GALLERY_API}/images", timeout=10)
    if response.status_code == 200:
        data = response.json()
        total = data.get("count", 0)
        images = data.get("images", [])
        recent = sorted(images, key=lambda x: x.get('created_at', ''), reverse=True)[:3]
        
        now = datetime.now()
        new_count = 0
        for img in recent:
            created_str = img.get('created_at', '')
            if created_str:
                try:
                    created = datetime.fromisoformat(created_str.split('.')[0])
                    diff_minutes = (now - created).total_seconds() / 60
                    if diff_minutes < 60:  # 1時間以内
                        new_count += 1
                        print(f"   [NEW] {img.get('filename', 'N/A')} - {diff_minutes:.1f}分前")
                except Exception:
                    pass
        
        print(f"   総画像数: {total}枚")
        print(f"   最近1時間以内: {new_count}枚")
        if new_count == 0:
            print("   [注意] 最近1時間以内に生成された画像はありません。")
except Exception as e:
    print(f"   確認エラー: {e}")

print()
print("=" * 60)
print("まとめ")
print("=" * 60)
print()
print("現在の状況:")
print("  - ジョブは送信されていますが、ComfyUIで処理されていない可能性があります")
print("  - エンコーディングエラーが発生している可能性が高いです")
print()
print("解決方法:")
print("  ComfyUIを再起動してください:")
print("    powershell -ExecutionPolicy Bypass -File start_comfyui_fixed.ps1")
print()
print("再起動後、生成状況を確認:")
print("    python check_all_recent_jobs.py")
