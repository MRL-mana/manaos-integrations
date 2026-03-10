#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最新の画像をブラウザで開く"""

import requests
import sys
import io
import webbrowser

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

from _paths import GALLERY_PORT

GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/images"  # type: ignore[name-defined]

try:
    response = requests.get(GALLERY_API)
    if response.status_code == 200:
        data = response.json()
        images = sorted(data['images'], key=lambda x: x['created_at'], reverse=True)

        print(f"最新の10枚の画像を開きます（全{len(images)}枚中）")
        print("=" * 60)

        for i, img in enumerate(images[:10], 1):
            url = f"http://127.0.0.1:5559/images/{img['filename']}"
            print(f"{i}. {img['filename']}")
            print(f"   URL: {url}")
            print(f"   サイズ: {img['size']:,} bytes")
            print(f"   作成日時: {img['created_at']}")
            print()

            # ブラウザで開く
            webbrowser.open(url)

        print("=" * 60)
        print("画像一覧ページも開きます...")
        webbrowser.open("http://127.0.0.1:5559/api/images")
    else:
        print(f"エラー: HTTP {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"エラー: {e}")
