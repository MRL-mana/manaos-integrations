#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aiServiceキーからチャットデータを抽出
"""
import sqlite3
import json
from pathlib import Path
import os
from datetime import datetime

db_path = Path(os.getenv('APPDATA')) / "Cursor" / "User" / "workspaceStorage" / "4592916e483577d5bb691bfc8bb37c7d" / "state.vscdb"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# aiService.generationsを取得
cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.generations'")
value = cursor.fetchone()

if value:
    try:
        if isinstance(value[0], bytes):
            data = json.loads(value[0].decode('utf-8'))
        else:
            data = json.loads(value[0])
        
        print(f"aiService.generationsのデータ構造:")
        print(f"  型: {type(data).__name__}")
        
        if isinstance(data, list):
            print(f"  リスト長: {len(data)}")
            if len(data) > 0:
                print(f"\n最初の3件のサンプル:")
                for i, item in enumerate(data[:3], 1):
                    print(f"\n  {i}. {item}")
        elif isinstance(data, dict):
            print(f"  キー: {list(data.keys())}")
            print(f"\nデータ内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print(f"パースエラー: {e}")
        import traceback
        traceback.print_exc()

# aiService.promptsも確認
cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.prompts'")
value = cursor.fetchone()

if value:
    try:
        if isinstance(value[0], bytes):
            data = json.loads(value[0].decode('utf-8'))
        else:
            data = json.loads(value[0])
        
        print(f"\n\naiService.promptsのデータ構造:")
        print(f"  型: {type(data).__name__}")
        
        if isinstance(data, list):
            print(f"  リスト長: {len(data)}")
            if len(data) > 0:
                print(f"\n最初の3件のサンプル:")
                for i, item in enumerate(data[:3], 1):
                    print(f"\n  {i}. {item}")
        elif isinstance(data, dict):
            print(f"  キー: {list(data.keys())}")
            print(f"\nデータ内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print(f"パースエラー: {e}")

conn.close()
