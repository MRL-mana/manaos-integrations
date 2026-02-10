#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gallery APIサーバーを再起動"""

import os
import subprocess
import time
import requests
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559"

print("=" * 60)
print("Gallery APIサーバー再起動")
print("=" * 60)
print()

# 1. 現在の状態確認
print("1. 現在の状態確認:")
try:
    response = requests.get(f"{GALLERY_API}/api/images", timeout=2)
    if response.status_code == 200:
        print("   [OK] Gallery APIは起動しています")
    else:
        print(f"   [WARN] Gallery API応答異常: {response.status_code}")
except:
    print("   [WARN] Gallery APIに接続できません")

print()

# 2. 再起動の案内
print("2. Gallery APIサーバーの再起動:")
print("   以下のコマンドで再起動してください:")
print()
print("   新しいコマンドプロンプトで:")
integrations_dir = os.getenv("MANAOS_INTEGRATIONS_DIR", str(Path(__file__).resolve().parent))
print(f"     cd {integrations_dir}")
print("     python gallery_api_server.py")
print()
print("   または、既存のプロセスを停止してから:")
print("     1. タスクマネージャーでpython.exeを探す")
print("     2. gallery_api_server.pyを実行しているプロセスを終了")
print("     3. 上記コマンドで再起動")
print()
