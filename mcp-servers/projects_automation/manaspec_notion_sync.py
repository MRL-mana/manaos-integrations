#!/usr/bin/env python3
"""
ManaSpec × Notion Integration (Skeleton)
OPENSPECの仕様をNotionに同期

TODO: Notion API認証情報の設定が必要
"""

import os
from pathlib import Path

# Notion API設定（環境変数から取得）
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

class ManaSpecNotionSync:
    """Notion同期クラス（スケルトン実装）"""
    
    def __init__(self, api_key: str = None, database_id: str = None):
        self.api_key = api_key or NOTION_API_KEY
        self.database_id = database_id or NOTION_DATABASE_ID
        
        if not self.api_key:
            print("⚠️ NOTION_API_KEY が設定されていません")
        if not self.database_id:
            print("⚠️ NOTION_DATABASE_ID が設定されていません")
    
    def sync_specs(self, openspec_path: str = "/root/openspec_test"):
        """Specsを Notion に同期"""
        print(f"📝 Specs同期開始: {openspec_path}")
        
        specs_dir = Path(openspec_path) / "openspec" / "specs"
        if not specs_dir.exists():
            print(f"❌ Specs directory not found: {specs_dir}")
            return
        
        # TODO: Notion API呼び出し実装
        print("⏸️  Notion API統合は未実装")
        print("実装方法:")
        print("  1. Notion Integration作成 (https://www.notion.so/my-integrations)")
        print("  2. NOTION_API_KEY を環境変数に設定")
        print("  3. Database作成 & ID取得")
        print("  4. requests/notion-client でAPI呼び出し")
    
    def sync_changes(self, openspec_path: str = "/root/openspec_test"):
        """Changesを Notion に同期"""
        print(f"📋 Changes同期開始: {openspec_path}")
        
        changes_dir = Path(openspec_path) / "openspec" / "changes"
        if not changes_dir.exists():
            print(f"❌ Changes directory not found: {changes_dir}")
            return
        
        # TODO: Notion API呼び出し実装
        print("⏸️  Notion API統合は未実装")


if __name__ == '__main__':
    sync = ManaSpecNotionSync()
    
    print("\n" + "="*60)
    print("ManaSpec × Notion Sync (Skeleton)")
    print("="*60 + "\n")
    
    sync.sync_specs()
    sync.sync_changes()
    
    print("\n" + "="*60)
    print("セットアップ手順:")
    print("="*60)
    print("1. Notion Integration作成:")
    print("   https://www.notion.so/my-integrations")
    print("\n2. 環境変数設定:")
    print("   export NOTION_API_KEY='secret_xxx'")
    print("   export NOTION_DATABASE_ID='xxx'")
    print("\n3. Databaseテンプレート:")
    print("   - Name (Title)")
    print("   - Type (Select: Spec/Change/Archive)")
    print("   - Status (Select: Proposed/Active/Completed)")
    print("   - Content (Text)")
    print("   - Created (Date)")

