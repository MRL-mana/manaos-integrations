#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian CLI ヘルパー
Obsidianノートの作成・検索・管理をCLIから実行
"""

import os
import sys
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from obsidian_integration import ObsidianIntegration
except ImportError:
    print("⚠️  obsidian_integration.pyが見つかりません")
    sys.exit(1)


def create_note(args):
    """ノートを作成"""
    vault_path = args.vault_path or os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "C:/Users/mana4/Documents/Obsidian Vault"
    )
    
    obsidian = ObsidianIntegration(vault_path)
    if not obsidian.is_available():
        print(f"❌ Obsidian Vaultが見つかりません: {vault_path}")
        return 1
    
    # コンテンツ読み込み
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    elif args.content:
        content = args.content
    else:
        print("❌ --file または --content を指定してください")
        return 1
    
    note_path = obsidian.create_note(
        title=args.title,
        content=content,
        tags=args.tags,
        folder=args.folder
    )
    
    if note_path:
        print(f"✅ ノート作成完了: {note_path}")
        return 0
    else:
        print("❌ ノート作成失敗")
        return 1


def search_notes(args):
    """ノートを検索"""
    vault_path = args.vault_path or os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "C:/Users/mana4/Documents/Obsidian Vault"
    )
    
    obsidian = ObsidianIntegration(vault_path)
    if not obsidian.is_available():
        print(f"❌ Obsidian Vaultが見つかりません: {vault_path}")
        return 1
    
    results = obsidian.search_notes(args.query, folder=args.folder)
    
    if results:
        print(f"📝 {len(results)}件のノートが見つかりました:")
        for note_path in results:
            print(f"  - {note_path}")
        return 0
    else:
        print("📝 ノートが見つかりませんでした")
        return 0


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Obsidian CLI ヘルパー")
    parser.add_argument(
        "--vault-path",
        help="Obsidian Vaultのパス（デフォルト: 環境変数OBSIDIAN_VAULT_PATH）"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # create コマンド
    create_parser = subparsers.add_parser("create", help="ノートを作成")
    create_parser.add_argument("title", help="ノートタイトル")
    create_parser.add_argument("--content", help="ノート内容")
    create_parser.add_argument("--file", help="ノート内容ファイル")
    create_parser.add_argument("--tags", nargs="+", help="タグリスト")
    create_parser.add_argument("--folder", help="フォルダ名")
    create_parser.set_defaults(func=create_note)
    
    # search コマンド
    search_parser = subparsers.add_parser("search", help="ノートを検索")
    search_parser.add_argument("query", help="検索クエリ")
    search_parser.add_argument("--folder", help="検索フォルダ")
    search_parser.set_defaults(func=search_notes)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
