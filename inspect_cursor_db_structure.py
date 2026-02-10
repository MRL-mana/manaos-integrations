#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursorデータベース構造を調査するスクリプト
"""
import os
import sqlite3
import json
from pathlib import Path

def inspect_db_structure(db_path: Path):
    """データベース構造を調査"""
    print(f"\n{'='*80}")
    print(f"データベース: {db_path}")
    print(f"{'='*80}\n")
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # テーブル一覧
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"テーブル一覧:")
        for table in tables:
            print(f"  - {table['name']}")
        print()
        
        # ItemTableの構造を確認
        if any(t['name'] == 'ItemTable' for t in tables):
            cursor.execute("PRAGMA table_info(ItemTable)")
            columns = cursor.fetchall()
            print("ItemTableのカラム:")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
            print()
            
            # サンプルデータを取得
            cursor.execute("SELECT key, value FROM ItemTable LIMIT 10")
            rows = cursor.fetchall()
            print("サンプルデータ（最初の10件）:")
            for i, row in enumerate(rows, 1):
                key = row['key']
                value = row['value']
                value_preview = str(value)[:100] if value else "NULL"
                print(f"\n{i}. Key: {key}")
                print(f"   Value (preview): {value_preview}...")
                
                # JSONとしてパース可能か試す
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            print(f"   JSON keys: {list(parsed.keys())[:10]}")
                        elif isinstance(parsed, list):
                            print(f"   JSON list length: {len(parsed)}")
                    except Exception:
                        pass
        
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
    
    inspect_db_structure(latest_workspace[2])

if __name__ == "__main__":
    main()
