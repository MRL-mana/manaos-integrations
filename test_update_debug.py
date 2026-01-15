#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース更新デバッグスクリプト
"""

import sys
import traceback
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_schemas import FileStatus, FileType, AuditAction

def main():
    """メイン処理"""
    print("=== データベース更新デバッグ ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # ファイルを取得
    files = db.get_files_by_status(FileStatus.TRIAGED, limit=1)
    if not files:
        print("整理対象のファイルがありません")
        return
    
    file_record = files[0]
    print(f"対象ファイル:")
    print(f"  ID: {file_record.id}")
    print(f"  名前: {file_record.original_name}")
    print(f"  ステータス: {file_record.status.value}")
    print(f"  タグ: {file_record.tags}")
    print(f"  alias: {file_record.alias_name}")
    
    # 更新前の状態を確認
    print(f"\n更新前の状態:")
    before = db.get_file_record(file_record.id)
    print(f"  ステータス: {before.status.value}")
    print(f"  タグ: {before.tags}")
    print(f"  alias: {before.alias_name}")
    
    # ファイルレコードを更新
    print(f"\n更新実行...")
    file_record.status = FileStatus.ARCHIVED
    file_record.tags = ["テスト"]
    file_record.alias_name = "2026-01-03_テスト_test.txt"
    file_record.add_audit_log(
        AuditAction.ARCHIVED,
        user="test_user",
        details={"test": True}
    )
    
    try:
        result = db.update_file_record(file_record)
        print(f"更新結果: {result}")
        
        if result:
            print("✅ 更新成功")
        else:
            print("❌ 更新失敗")
            # エラーの詳細を確認
            import sqlite3
            cursor = db.conn.cursor()
            cursor.execute("SELECT rowid FROM file_records WHERE id = ?", (file_record.id,))
            row = cursor.fetchone()
            print(f"rowid取得: {row[0] if row else 'None'}")
        
        # 更新後の状態を確認
        print(f"\n更新後の状態:")
        after = db.get_file_record(file_record.id)
        if after:
            print(f"  ステータス: {after.status.value}")
            print(f"  タグ: {after.tags}")
            print(f"  alias: {after.alias_name}")
            print(f"  監査ログ数: {len(after.audit_log)}")
        else:
            print("  ファイルが見つかりません")
            
    except Exception as e:
        print(f"\nエラー発生:")
        traceback.print_exc()
    
    db.close()

if __name__ == '__main__':
    main()






















