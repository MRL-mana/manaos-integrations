#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理機能最終テスト
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
    files = db.get_files_by_status(FileStatus.TRIAGED, limit=1)
    
    if not files:
        print("No files to organize")
        return
    
    print(f"Found {len(files)} files to organize")
    print(f"File: {files[0].original_name}")
    print(f"Status before: {files[0].status.value}")
    
    org = FileOrganizer(db)
    result = org.organize_files([files[0].id], user='test')
    
    print(f"\nResult:")
    print(f"  Status: {result.get('status')}")
    print(f"  Organized count: {result.get('organized_count')}")
    
    if result.get('files'):
        for f in result.get('files'):
            print(f"\nOrganized file:")
            print(f"  Original: {f.get('original_name')}")
            print(f"  Alias: {f.get('alias_name')}")
            print(f"  Tags: {f.get('tags')}")
            print(f"  Status: {f.get('status')}")
    
    updated = db.get_file_record(files[0].id)
    if updated:
        print(f"\nDatabase check:")
        print(f"  Status: {updated.status.value}")
        print(f"  Alias: {updated.alias_name}")
        print(f"  Tags: {updated.tags}")
    
    db.close()

if __name__ == '__main__':
    main()

