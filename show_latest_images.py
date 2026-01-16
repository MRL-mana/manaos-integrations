#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最新の画像を表示"""

import requests
import sys
import io
import webbrowser
import time

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/images"

try:
    response = requests.get(GALLERY_API)
    if response.status_code == 200:
        data = response.json()
        images = sorted(data['images'], key=lambda x: x['created_at'], reverse=True)

        print("=" * 60)
        print(f"最新の10枚の画像を表示します（全{len(images)}枚中）")
        print("=" * 60)
        print()

        # 最新の10枚の画像URLを開く
        for i, img in enumerate(images[:10], 1):
            url = f"http://localhost:5559/images/{img['filename']}"
            print(f"{i}. {img['filename']}")
            print(f"   URL: {url}")

            if 'prompt' in img:
                prompt_preview = img['prompt'][:80] + "..." if len(img['prompt']) > 80 else img['prompt']
                print(f"   プロンプト: {prompt_preview}")

            print()

            # 少し間隔を空けてブラウザで開く
            if i <= 5:  # 最初の5枚だけ開く（多すぎると重い）
                webbrowser.open(url)
                time.sleep(0.5)

        print("=" * 60)
        print("ギャラリーページも開きます...")
        webbrowser.open("http://localhost:5559/")
    else:
        print(f"エラー: HTTP {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
