#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理機能デバッグスクリプト
"""

import sys
import traceback
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileStatus

def main():
    """メイン処理"""
    print("=== File Secretary 整理機能デバッグ ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # 整理対象ファイルを取得
    files = db.get_files_by_status(FileStatus.TRIAGED, limit=5)
    print(f"整理対象ファイル数: {len(files)}")
    
    if not files:
        print("整理対象のファイルがありません")
        return
    
    file_record = files[0]
    print(f"\n対象ファイル:")
    print(f"  ID: {file_record.id}")
    print(f"  名前: {file_record.original_name}")
    print(f"  ステータス: {file_record.status.value}")
    print(f"  タグ: {file_record.tags}")
    print(f"  alias: {file_record.alias_name}")
    
    # Organizer初期化
    organizer = FileOrganizer(db)
    
    # タグ推定テスト
    print(f"\nタグ推定テスト:")
    tags = organizer._infer_tags_simple(file_record)
    print(f"  推定タグ: {tags}")
    
    # alias生成テスト
    print(f"\nalias生成テスト:")
    alias = organizer._generate_alias_name(file_record, tags)
    print(f"  生成alias: {alias}")
    
    # 整理実行（1ファイルのみ）
    print(f"\n整理実行...")
    try:
        result = organizer.organize_files(
            file_ids=[file_record.id],
            user='test_user',
            auto_tag=True,
            auto_alias=True
        )
        
        print(f"\n結果:")
        print(f"  ステータス: {result.get('status')}")
        print(f"  整理済み数: {result.get('organized_count', 0)}")
        print(f"  エラー: {result.get('error', 'なし')}")
        
        if result.get('files'):
            for file_info in result.get('files', []):
                print(f"\n整理されたファイル:")
                print(f"  ID: {file_info.get('id')}")
                print(f"  元の名前: {file_info.get('original_name')}")
                print(f"  alias: {file_info.get('alias_name')}")
                print(f"  タグ: {file_info.get('tags')}")
                print(f"  ステータス: {file_info.get('status')}")
        
        # データベースから再取得して確認
        print(f"\nデータベース確認:")
        updated_file = db.get_file_record(file_record.id)
        if updated_file:
            print(f"  ステータス: {updated_file.status.value}")
            print(f"  タグ: {updated_file.tags}")
            print(f"  alias: {updated_file.alias_name}")
        else:
            print("  ファイルが見つかりません")
            
    except Exception as e:
        print(f"\nエラー発生:")
        traceback.print_exc()
    
    db.close()

if __name__ == '__main__':
    main()

