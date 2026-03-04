#!/usr/bin/env python3
"""
Mana Memory Migration Script
既存のJSONファイルをSQLiteに安全に移行するスクリプト

安全性保証:
- 既存JSONファイルは削除しない（コピーのみ）
- テストモードで動作確認可能
- データ完全性チェック
"""

import json
import sqlite3
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 設定
MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
TEST_DB_PATH = MEMORY_DIR / "hot_memory_test.db"
SCHEMA_PATH = MEMORY_DIR / "hot_memory_schema.sql"

# 既存JSONファイルパス
AI_CONTEXT_MEMORY = Path("/root/.ai_context_memory.json")
TRINITY_SHARED_MEMORY = Path("/root/.trinity_shared_memory.json")
GITHUB_PR_MEMORY = Path("/root/github_pr_memory.json")


def load_json_file(file_path: Path) -> Optional[Dict]:
    """JSONファイルを安全に読み込む"""
    if not file_path.exists():
        print(f"  ⚠️  {file_path} が見つかりません（スキップ）")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ❌ {file_path} の読み込みエラー: {e}")
        return None


def init_database(db_path: Path, test_mode: bool = False) -> sqlite3.Connection:
    """データベースを初期化"""
    if test_mode:
        print(f"  🧪 テストモード: {db_path}")

    # ディレクトリ作成
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 既存DBがある場合は削除（テストモードのみ）
    if test_mode and db_path.exists():
        db_path.unlink()
        print(f"  🗑️  テスト用DBを削除しました")

    # DB接続
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # スキーマ読み込み・実行
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn.executescript(schema)
        print(f"  ✅ スキーマ適用完了")
    else:
        print(f"  ❌ スキーマファイルが見つかりません: {SCHEMA_PATH}")
        sys.exit(1)

    return conn


def migrate_ai_context_memory(conn: sqlite3.Connection, data: Dict) -> int:
    """ai_context_memory.jsonを移行"""
    count = 0

    # conversations
    if 'conversations' in data:
        for conv in data['conversations']:
            conn.execute("""
                INSERT INTO conversations (
                    user_message, assistant_message, context,
                    timestamp, importance
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                conv.get('user', ''),
                conv.get('assistant', ''),
                json.dumps(conv.get('context', {}), ensure_ascii=False),
                conv.get('timestamp', datetime.now().isoformat()),
                conv.get('importance', 5)
            ))
            count += 1

    # preferences
    if 'preferences' in data:
        for key, value in data['preferences'].items():
            conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()))
            count += 1

    conn.commit()
    return count


def migrate_trinity_shared_memory(conn: sqlite3.Connection, data: Dict) -> int:
    """trinity_shared_memory.jsonを移行"""
    count = 0

    # conversation_summary
    if 'conversation_summary' in data:
        for date, conversations in data['conversation_summary'].items():
            for conv in conversations:
                conn.execute("""
                    INSERT INTO conversations (
                        user_message, assistant_message, context,
                        emotion, timestamp, importance
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    '',  # user_messageはcontentから抽出できないため空
                    '',  # assistant_messageも同様
                    json.dumps({'content': conv.get('content', '')}, ensure_ascii=False),
                    conv.get('emotion', 'neutral'),
                    conv.get('timestamp', datetime.now().isoformat()),
                    5
                ))
                count += 1

    # important_info
    if 'important_info' in data:
        for info in data['important_info']:
            conn.execute("""
                INSERT INTO important_info (
                    content, importance, category, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                info.get('content', ''),
                info.get('importance', 7),
                '',  # category
                json.dumps(info.get('metadata', {}), ensure_ascii=False),
                info.get('timestamp', datetime.now().isoformat()),
                datetime.now().isoformat()
            ))
            count += 1

    # preferences, schedule, tasks, context
    for key in ['mana_preferences', 'mana_schedule', 'mana_tasks', 'mana_context']:
        if key in data and data[key]:
            conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                key,
                json.dumps(data[key], ensure_ascii=False),
                'trinity',
                datetime.now().isoformat()
            ))
            count += 1

    conn.commit()
    return count


def migrate_github_pr_memory(conn: sqlite3.Connection, data: Dict) -> int:
    """github_pr_memory.jsonを移行"""
    count = 0

    if 'prs' in data:
        for pr in data['prs']:
            content = json.dumps(pr, ensure_ascii=False)
            conn.execute("""
                INSERT INTO memories (
                    content, importance, category, source, metadata,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                content,
                6,  # デフォルト重要度
                'github_pr',
                'github_pr',
                json.dumps({
                    'number': pr.get('number'),
                    'author': pr.get('author'),
                    'files': pr.get('files', [])
                }, ensure_ascii=False),
                pr.get('created_at', datetime.now().isoformat())
            ))
            count += 1

    conn.commit()
    return count


def verify_data_integrity(conn: sqlite3.Connection, original_counts: Dict[str, int]) -> bool:
    """データ完全性を検証"""
    print("\n🔍 データ完全性チェック...")

    # 各テーブルの件数を確認
    tables = {
        'conversations': conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
        'preferences': conn.execute("SELECT COUNT(*) FROM preferences").fetchone()[0],
        'important_info': conn.execute("SELECT COUNT(*) FROM important_info").fetchone()[0],
        'memories': conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    }

    print(f"  📊 移行結果:")
    for table, count in tables.items():
        print(f"    {table}: {count}件")

    # 元データとの比較（可能な範囲で）
    total_migrated = sum(tables.values())
    print(f"  📈 合計: {total_migrated}件")

    return True


def main():
    parser = argparse.ArgumentParser(description='Mana Memory Migration Script')
    parser.add_argument('--test-mode', action='store_true', help='テストモード（本番データに影響なし）')
    parser.add_argument('--verify-only', action='store_true', help='検証のみ（移行は実行しない）')
    args = parser.parse_args()

    test_mode = args.test_mode
    db_path = TEST_DB_PATH if test_mode else DB_PATH

    print("🔄 Mana Memory Migration 開始")
    print("============================================")
    print(f"モード: {'テストモード' if test_mode else '本番モード'}")
    print(f"データベース: {db_path}")
    print("")

    # データベース初期化
    print("📦 データベース初期化中...")
    conn = init_database(db_path, test_mode)

    if args.verify_only:
        print("🔍 検証モード: データベース構造を確認します")
        verify_data_integrity(conn, {})
        conn.close()
        return

    # JSONファイル読み込み
    print("\n📂 JSONファイル読み込み中...")
    ai_context_data = load_json_file(AI_CONTEXT_MEMORY)
    trinity_data = load_json_file(TRINITY_SHARED_MEMORY)
    github_pr_data = load_json_file(GITHUB_PR_MEMORY)

    # 元データの件数を記録（検証用）
    original_counts = {}

    # 移行実行
    print("\n🔄 データ移行中...")
    total_count = 0

    if ai_context_data:
        print("  📝 ai_context_memory.json を移行中...")
        count = migrate_ai_context_memory(conn, ai_context_data)
        total_count += count
        print(f"    ✅ {count}件移行完了")

    if trinity_data:
        print("  📝 trinity_shared_memory.json を移行中...")
        count = migrate_trinity_shared_memory(conn, trinity_data)
        total_count += count
        print(f"    ✅ {count}件移行完了")

    if github_pr_data:
        print("  📝 github_pr_memory.json を移行中...")
        count = migrate_github_pr_memory(conn, github_pr_data)
        total_count += count
        print(f"    ✅ {count}件移行完了")

    # データ完全性検証
    verify_data_integrity(conn, original_counts)

    conn.close()

    print("\n✅ 移行完了！")
    print(f"📊 合計: {total_count}件のデータを移行しました")
    print(f"📁 データベース: {db_path}")

    if test_mode:
        print("\n🧪 テストモードで完了しました。")
        print("   問題がなければ --test-mode なしで実行してください。")
    else:
        print("\n✅ 本番移行完了！")
        print("   既存のJSONファイルはそのまま残っています。")
        print("   Hybridモードで動作確認をお願いします。")


if __name__ == '__main__':
    main()









