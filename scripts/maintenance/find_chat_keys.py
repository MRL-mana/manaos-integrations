#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursorデータベースからチャット関連のキーを検索
"""
import os
import sqlite3
import json
from pathlib import Path

def find_chat_keys(db_path: Path):
    """チャット関連のキーを検索"""
    print(f"\n{'='*80}")
    print(f"データベース: {db_path}")
    print(f"{'='*80}\n")
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # チャット関連のキーを検索
        cursor.execute("SELECT key FROM ItemTable WHERE key LIKE '%chat%' OR key LIKE '%Chat%' OR key LIKE '%CHAT%'")
        chat_keys = cursor.fetchall()
        
        print(f"チャット関連のキー ({len(chat_keys)}件):")
        for row in chat_keys:
            print(f"  - {row['key']}")
        print()
        
        # composer関連のキーを検索
        cursor.execute("SELECT key FROM ItemTable WHERE key LIKE '%composer%' OR key LIKE '%Composer%'")
        composer_keys = cursor.fetchall()
        
        print(f"Composer関連のキー ({len(composer_keys)}件):")
        for row in composer_keys:
            print(f"  - {row['key']}")
        print()
        
        # すべてのキーを取得して、チャットらしきものを探す
        cursor.execute("SELECT key FROM ItemTable")
        all_keys = [row['key'] for row in cursor.fetchall()]
        
        # 怪しそうなキーを探す
        suspicious_keys = []
        for key in all_keys:
            if any(term in key.lower() for term in ['message', 'conversation', 'prompt', 'ai', 'claude', 'assistant', 'user']):
                suspicious_keys.append(key)
        
        if suspicious_keys:
            print(f"その他の怪しいキー ({len(suspicious_keys)}件):")
            for key in suspicious_keys[:20]:  # 最初の20件
                print(f"  - {key}")
            print()
        
        # composerChatViewPaneのデータを詳しく見る
        cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%composerChatViewPane%'")
        composer_data = cursor.fetchall()
        
        if composer_data:
            print(f"\nComposerChatViewPaneのデータ ({len(composer_data)}件):")
            for row in composer_data:
                print(f"\nキー: {row['key']}")
                value = row['value']
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except Exception:
                        value = str(value)[:200]
                
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        print(f"  JSON構造:")
                        if isinstance(parsed, dict):
                            print(f"    キー一覧: {list(parsed.keys())[:20]}")
                            # チャットらしきデータを探す
                            for k, v in parsed.items():
                                if isinstance(v, (dict, list)) and len(str(v)) > 100:
                                    print(f"    {k}: {type(v).__name__} (size: {len(str(v))})")
                        elif isinstance(parsed, list):
                            print(f"    リスト長: {len(parsed)}")
                            if len(parsed) > 0:
                                print(f"    最初の要素: {type(parsed[0]).__name__}")
                    except json.JSONDecodeError:
                        print(f"  (JSONではない)")
        
        conn.close()
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    appdata = os.getenv('APPDATA')
    workspace_storage = Path(appdata) / "Cursor" / "User" / "workspaceStorage"
    
    # 最新のワークスペースを確認
    workspaces = []
    for ws_dir in workspace_storage.iterdir():
        if not ws_dir.is_dir():
            continue
        db_path = ws_dir / "state.vscdb"
        if db_path.exists():
            mtime = db_path.stat().st_mtime
            workspaces.append((mtime, ws_dir.name, db_path))
    
    if not workspaces:
        print("ワークスペースが見つかりません")
        return
    
    # 最新のワークスペースを調査
    workspaces.sort(reverse=True)
    latest_workspace = workspaces[0]
    print(f"最新のワークスペース: {latest_workspace[1]}")
    
    find_chat_keys(latest_workspace[2])

if __name__ == "__main__":
    main()
