#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursorデータベースからチャットデータを包括的に検索
"""
import sqlite3
import json
from pathlib import Path
import os

db_path = Path(os.getenv('APPDATA')) / "Cursor" / "User" / "workspaceStorage" / "4592916e483577d5bb691bfc8bb37c7d" / "state.vscdb"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# すべてのキーを取得
cursor.execute("SELECT key FROM ItemTable")
all_keys = [row[0] for row in cursor.fetchall()]

print(f"総キー数: {len(all_keys)}\n")

# チャットらしきキーを探す
chat_like_keys = []
for key in all_keys:
    key_lower = key.lower()
    if any(term in key_lower for term in ['chat', 'message', 'conversation', 'prompt', 'ai', 'claude', 'assistant']):
        chat_like_keys.append(key)

print(f"チャットらしきキー ({len(chat_like_keys)}件):\n")
for key in chat_like_keys[:30]:  # 最初の30件
    print(f"  - {key}")
    
    # データサイズを確認
    cursor.execute("SELECT LENGTH(value) FROM ItemTable WHERE key = ?", (key,))
    size = cursor.fetchone()[0]
    print(f"    サイズ: {size} bytes")
    
    # データの一部を確認
    cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
    value = cursor.fetchone()
    if value and size > 100:  # 100バイト以上のデータのみ
        try:
            if isinstance(value[0], bytes):
                data_str = value[0].decode('utf-8', errors='ignore')[:500]
            else:
                data_str = str(value[0])[:500]
            
            # JSONとしてパース可能か試す
            try:
                if isinstance(value[0], bytes):
                    data = json.loads(value[0].decode('utf-8'))
                else:
                    data = json.loads(value[0])
                
                if isinstance(data, dict):
                    keys_list = list(data.keys())[:10]
                    print(f"    JSONキー: {keys_list}")
                    # チャットらしきキーがあるか確認
                    if any(k in keys_list for k in ['messages', 'content', 'text', 'role', 'user', 'assistant']):
                        print(f"    ⭐⭐ チャットデータの可能性が高い!")
                elif isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        keys_list = list(data[0].keys())[:10]
                        print(f"    リスト要素のキー: {keys_list}")
                        if any(k in keys_list for k in ['messages', 'content', 'text', 'role', 'user', 'assistant']):
                            print(f"    ⭐⭐ チャットデータの可能性が高い!")
            except Exception:
                # JSONでない場合は文字列の一部を表示
                if 'user' in data_str.lower() or 'assistant' in data_str.lower() or 'message' in data_str.lower():
                    print(f"    プレビュー: {data_str[:200]}...")
        except Exception as e:
            pass
    print()

conn.close()
