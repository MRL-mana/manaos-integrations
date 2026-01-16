#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI再起動後の自動確認と画像生成状況チェック"""

import requests
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
GALLERY_API = "http://localhost:5559/api/images"

print("=" * 60)
print("ComfyUI再起動後の確認")
print("=" * 60)
print()

# 1. ComfyUI接続確認
print("1. ComfyUI接続確認:")
for i in range(10):
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        if response.status_code == 200:
            stats = response.json()
            system = stats.get("system", {})
            print(f"   [OK] ComfyUI接続成功")
            print(f"   ComfyUIバージョン: {system.get('comfyui_version', 'N/A')}")
            break
    except:
        if i < 9:
            print(f"   接続試行 {i+1}/10...")
            time.sleep(3)
        else:
            print("   [ERROR] ComfyUIに接続できません")
            print("   ComfyUIが起動しているか確認してください")
            sys.exit(1)

print()

# 2. エラー状況確認
print("2. 最新のエラー状況:")
try:
    response = requests.get(f"{COMFYUI_URL}/history", timeout=5)
    if response.status_code == 200:
        history = response.json()
        if history:
            items = list(history.items())[-5:]
            encoding_errors = 0
            other_errors = 0
            for prompt_id, data in items:
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                if status_str == "error":
                    messages = status.get("messages", [])
                    for msg in messages:
                        if msg[0] == "execution_error":
                            error_data = msg[1]
                            error_msg = error_data.get('exception_message', 'N/A')
                            if "Invalid argument" in error_msg or "Errno 22" in error_msg:
                                encoding_errors += 1
                            else:
                                other_errors += 1
                            break
            
            print(f"   エンコーディングエラー: {encoding_errors}件")
            print(f"   その他のエラー: {other_errors}件")
            
            if encoding_errors > 0:
                print()
                print("   [WARN] まだエンコーディングエラーが発生しています")
                print("   ComfyUIが正しく再起動されていない可能性があります")
                print("   環境変数を設定して再起動してください:")
                print("     cd C:\\ComfyUI")
                print("     set PYTHONIOENCODING=utf-8")
                print("     set PYTHONLEGACYWINDOWSSTDIO=1")
                print("     python main.py")
            else:
                print("   [OK] 最近のエンコーディングエラーは見つかりませんでした")
except:
    pass

print()

# 3. キュー状態確認
print("3. ComfyUIキュー状態:")
try:
    response = requests.get(f"{COMFYUI_URL}/queue", timeout=5)
    if response.status_code == 200:
        queue = response.json()
        running = queue.get("queue_running", [])
        pending = queue.get("queue_pending", [])
        print(f"   実行中: {len(running)}件")
        print(f"   待機中: {len(pending)}件")
    else:
        print(f"   [ERROR] HTTP {response.status_code}")
except:
    print("   [ERROR] キュー情報を取得できませんでした")

print()

# 4. 最新の画像確認
print("4. 最新の画像:")
try:
    response = requests.get(GALLERY_API, timeout=5)
    if response.status_code == 200:
        images = response.json()
        if isinstance(images, list):
            total = len(images)
            recent = [img for img in images if img.get('created_at', '')]
            if recent:
                recent.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                print(f"   総画像数: {total}枚")
                print(f"   最新5件:")
                for i, img in enumerate(recent[:5], 1):
                    filename = img.get('filename', 'N/A')
                    created = img.get('created_at', 'N/A')
                    print(f"     {i}. {filename}")
                    print(f"        作成日時: {created}")
            else:
                print(f"   総画像数: {total}枚")
        else:
            print("   [INFO] 画像データの形式が異なります")
    else:
        print(f"   [ERROR] HTTP {response.status_code}")
except Exception as e:
    print(f"   [ERROR] {e}")

print()
print("=" * 60)
print("確認完了")
print("=" * 60)
print()
print("画像生成を再試行するには:")
print("  python restart_comfyui_and_generate.py")
print()
print("または、新しいジョブを送信するには:")
print("  python fix_and_generate.py")
