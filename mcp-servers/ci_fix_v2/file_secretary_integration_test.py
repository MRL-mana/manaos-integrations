#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary 統合テスト
全機能の統合テストを実行
"""

import sys
import time
import httpx
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_indexer import FileIndexer
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileSource, FileStatus

try:
    from manaos_integrations._paths import FILE_SECRETARY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import FILE_SECRETARY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        FILE_SECRETARY_PORT = int(os.getenv("FILE_SECRETARY_PORT", "5120"))

def test_database():
    """データベーステスト"""
    print("=== データベーステスト ===")
    db = FileSecretaryDB('file_secretary_test.db')
    print("✅ データベース初期化成功")
    
    # 統計取得テスト
    status = db.get_inbox_status()
    print(f"  新規ファイル: {status['new_count']}件")
    print(f"  未処理ファイル: {status['old_count']}件")
    
    db.close()
    return True

def test_indexer():
    """Indexerテスト"""
    print("\n=== Indexerテスト ===")
    db = FileSecretaryDB('file_secretary_test.db')
    inbox_path = Path("00_INBOX")
    inbox_path.mkdir(exist_ok=True)
    
    # テストファイル作成
    test_file = inbox_path / "integration_test.txt"
    test_file.write_text("Integration test file", encoding='utf-8')
    
    indexer = FileIndexer(db, FileSource.MOTHER, str(inbox_path))
    count = indexer.index_directory()
    print(f"✅ インデックス完了: {count}件")
    
    db.close()
    return count > 0

def test_organizer():
    """Organizerテスト"""
    print("\n=== Organizerテスト ===")
    db = FileSecretaryDB('file_secretary_test.db')
    
    # 整理対象ファイル取得
    files = db.get_files_by_status(FileStatus.TRIAGED, limit=1)
    if not files:
        print("⚠️ 整理対象ファイルなし")
        db.close()
        return False
    
    org = FileOrganizer(db)
    result = org.organize_files([files[0].id], user='test')
    
    if result.get('status') == 'success' and result.get('organized_count') > 0:
        print(f"✅ 整理完了: {result.get('organized_count')}件")
        db.close()
        return True
    else:
        print(f"⚠️ 整理失敗: {result.get('error', 'unknown')}")
        db.close()
        return False

def test_restore():
    """復元テスト"""
    print("\n=== 復元テスト ===")
    db = FileSecretaryDB('file_secretary_test.db')
    
    # アーカイブ済みファイル取得
    files = db.get_files_by_status(FileStatus.ARCHIVED, limit=1)
    if not files:
        print("⚠️ アーカイブ済みファイルなし")
        db.close()
        return False
    
    org = FileOrganizer(db)
    result = org.restore_files([files[0].id], user='test')
    
    if result.get('status') == 'success' and result.get('restored_count') > 0:
        print(f"✅ 復元完了: {result.get('restored_count')}件")
        db.close()
        return True
    else:
        print(f"⚠️ 復元失敗: {result.get('error', 'unknown')}")
        db.close()
        return False

def test_api():
    """APIテスト"""
    print("\n=== APIテスト ===")
    api_url = os.getenv(
        "FILE_SECRETARY_URL",
        f"http://127.0.0.1:{FILE_SECRETARY_PORT}",
    )
    
    try:
        # ヘルスチェック
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ ヘルスチェック成功")
        else:
            print(f"⚠️ ヘルスチェック失敗: {response.status_code}")
            return False
        
        # INBOX状況取得
        response = httpx.get(f"{api_url}/api/inbox/status", timeout=5.0)
        if response.status_code == 200:
            print("✅ INBOX状況取得成功")
        else:
            print(f"⚠️ INBOX状況取得失敗: {response.status_code}")
            return False
        
        return True
    except httpx.ConnectError:
        print("⚠️ APIサーバーに接続できません（起動していない可能性があります）")
        return False
    except Exception as e:
        print(f"⚠️ APIテストエラー: {e}")
        return False

def test_slack_integration():
    """Slack統合テスト"""
    print("\n=== Slack統合テスト ===")
    
    try:
        from file_secretary_templates import parse_command, extract_search_query
        
        test_cases = [
            ("Inboxどう？", "status"),
            ("終わった", "done"),
            ("戻して", "restore"),
            ("探して：日報", "search")
        ]
        
        all_passed = True
        for text, expected in test_cases:
            cmd = parse_command(text)
            if cmd == expected:
                print(f"✅ \"{text}\" -> {cmd}")
            else:
                print(f"⚠️ \"{text}\" -> {cmd} (expected: {expected})")
                all_passed = False
        
        return all_passed
    except ImportError:
        print("⚠️ file_secretary_templatesモジュールが見つかりません")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("File Secretary 統合テスト")
    print("=" * 60)
    
    results = {}
    
    # テスト実行
    results['database'] = test_database()
    results['indexer'] = test_indexer()
    results['organizer'] = test_organizer()
    results['restore'] = test_restore()
    results['api'] = test_api()
    results['slack'] = test_slack_integration()
    
    # 結果サマリ
    print("\n" + "=" * 60)
    print("テスト結果サマリ")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "⚠️ SKIP/FAIL"
        print(f"{name:20s}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if passed == total:
        print("\n🎉 すべてのテストが通過しました！")
    else:
        print(f"\n⚠️ {total - passed}件のテストがスキップまたは失敗しました")

if __name__ == '__main__':
    main()






















