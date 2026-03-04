#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
復元機能テスト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileStatus

def main():
    db = FileSecretaryDB('file_secretary.db')
    
    # アーカイブ済みファイルを取得
    archived_files = db.get_files_by_status(FileStatus.ARCHIVED, limit=5)
    print(f"Archived files: {len(archived_files)}")
    
    if not archived_files:
        print("No archived files to restore")
        return
    
    target_file = archived_files[0]
    print(f"\nTarget file:")
    print(f"  ID: {target_file.id[:16]}...")
    print(f"  Name: {target_file.original_name}")
    print(f"  Alias: {target_file.alias_name}")
    print(f"  Status: {target_file.status.value}")
    
    # 復元実行
    org = FileOrganizer(db)
    result = org.restore_files([target_file.id], user='test')
    
    print(f"\nRestore result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Restored count: {result.get('restored_count')}")
    
    if result.get('files'):
        for f in result.get('files'):
            print(f"\nRestored file:")
            print(f"  ID: {f.get('id')[:16]}...")
            print(f"  Status: {f.get('status')}")
            print(f"  Restored from: {f.get('restored_from')}")
    
    # データベース確認
    restored = db.get_file_record(target_file.id)
    if restored:
        print(f"\nDatabase check:")
        print(f"  Status: {restored.status.value}")
        print(f"  Alias: {restored.alias_name}")
        print(f"  Audit log entries: {len(restored.audit_log)}")
    
    db.close()
























