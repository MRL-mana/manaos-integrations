#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Indexerテスト
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_drive_indexer import GoogleDriveIndexer

def main():
    print("=== Google Drive Indexer テスト ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # Google Drive Indexer初期化
    print("Google Drive Indexer初期化中...")
    indexer = GoogleDriveIndexer(db, drive_folder_name="INBOX")
    
    if not indexer.drive_integration or not indexer.drive_integration.is_available():
        print("⚠️ Google Drive統合が利用できません")
        print("   設定が必要:")
        print("   - GOOGLE_DRIVE_CREDENTIALS環境変数（credentials.jsonのパス）")
        print("   - GOOGLE_DRIVE_TOKEN環境変数（token.jsonのパス）")
        print("   - Google Drive APIの有効化")
        return
    
    print("✅ Google Drive統合利用可能\n")
    
    # フォルダ検索/作成
    print("INBOXフォルダ確認中...")
    if indexer.drive_folder_id:
        print(f"✅ INBOXフォルダID: {indexer.drive_folder_id}")
    else:
        print("⚠️ INBOXフォルダが見つかりませんでした")
        return
    
    # ファイル一覧取得
    print("\nファイル一覧取得中...")
    files = indexer.list_drive_files()
    print(f"ファイル数: {len(files)}")
    
    if files:
        print("\nファイル一覧:")
        for f in files[:5]:  # 最初の5件
            print(f"  - {f['name']} ({f['mime_type']}, {f['size']} bytes)")
    
    # ファイルインデックス（最初の1件のみ）
    if files:
        print(f"\nファイルインデックス実行中（最初の1件）...")
        file_record = indexer.index_drive_file(files[0]['id'])
        if file_record:
            print(f"✅ インデックス完了:")
            print(f"   ID: {file_record.id[:16]}...")
            print(f"   名前: {file_record.original_name}")
            print(f"   ステータス: {file_record.status.value}")
            print(f"   タイプ: {file_record.type.value if file_record.type else 'unknown'}")
        else:
            print("⚠️ インデックス失敗")
    
    db.close()

if __name__ == '__main__':
    main()






















