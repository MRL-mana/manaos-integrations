#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理機能テストスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileStatus

def main():
    """メイン処理"""
    print("=== File Secretary 整理機能テスト ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # 整理対象ファイルを取得
    files = db.get_files_by_status(FileStatus.TRIAGED, limit=5)
    print(f"整理対象ファイル数: {len(files)}")
    
    if not files:
        print("整理対象のファイルがありません")
        return
    
    # ファイルIDを表示
    file_ids = []
    for f in files:
        print(f"  - {f.original_name} (ID: {f.id[:16]}...)")
        file_ids.append(f.id)
    
    print(f"\n整理実行中...")
    
    # Organizer初期化
    organizer = FileOrganizer(db)
    
    # 整理実行
    result = organizer.organize_files(
        file_ids=file_ids[:2],  # 最初の2件を整理
        user='test_user',
        auto_tag=True,
        auto_alias=True
    )
    
    print(f"\n結果:")
    print(f"  ステータス: {result.get('status')}")
    print(f"  整理済み数: {result.get('organized_count', 0)}")
    
    if result.get('status') == 'success':
        print(f"\n整理されたファイル:")
        for file_info in result.get('files', []):
            print(f"  - {file_info.get('original_name')} -> {file_info.get('alias_name')}")
            print(f"    タグ: {file_info.get('tags')}")
            print(f"    ステータス: {file_info.get('status')}")
    
    # 整理後の状態確認
    print(f"\n整理後の状態確認:")
    archived_files = db.get_files_by_status(FileStatus.ARCHIVED, limit=5)
    print(f"  アーカイブ済み: {len(archived_files)}件")
    triaged_files = db.get_files_by_status(FileStatus.TRIAGED, limit=5)
    print(f"  未整理: {len(triaged_files)}件")
    
    db.close()

if __name__ == '__main__':
    main()

