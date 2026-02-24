#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHubクイックコマンド
よく使う操作を簡単に実行
"""

import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_helper import GitHubHelper
from github_integration import GitHubIntegration

def quick_commit_push(message: str = None):
    """クイックコミット・プッシュ"""
    helper = GitHubHelper()
    
    if not message:
        from datetime import datetime
        message = f"更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"コミット: {message}")
    if helper.auto_commit(message):
        print("✅ コミット完了")
        if helper.auto_push():
            print("✅ プッシュ完了")
        else:
            print("⚠️ プッシュに失敗")
    else:
        print("⚠️ コミットする変更がありません")

def quick_status():
    """クイックステータス確認"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    repo_info = github.get_repository("MRL-mana", "manaos-integrations")
    
    if repo_info:
        print(f"\n📦 {repo_info['name']}")
        print(f"   プライベート: {'✅' if repo_info.get('private') else '❌'}")
        print(f"   スター: {repo_info['stars']}")
        print(f"   フォーク: {repo_info['forks']}")
        print(f"   URL: {repo_info['url']}")
    
    # Gitステータス
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=True
    )
    
    if result.stdout.strip():
        print(f"\n📝 変更されたファイル:")
        print(result.stdout)
    else:
        print("\n✅ 変更なし")

def quick_issue(title: str, body: str = None, labels: str = None):
    """クイックイシュー作成"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    label_list = [l.strip() for l in labels.split(",")] if labels else []
    
    issue = github.create_issue(
        "MRL-mana", "manaos-integrations",
        title, body, label_list
    )
    
    if issue:
        print(f"✅ イシューを作成しました:")
        print(f"   #{issue['number']}: {issue['title']}")
        print(f"   URL: {issue['url']}")
    else:
        print("❌ イシューの作成に失敗しました")

def quick_release(tag: str, title: str = None):
    """クイックリリース作成"""
    if not title:
        title = f"Release {tag}"
    
    cmd = [
        "gh", "release", "create", tag,
        "--title", title,
        "--notes", f"リリース {tag}",
        "--repo", "MRL-mana/manaos-integrations"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ リリースを作成しました: {tag}")
    except Exception as e:
        print(f"❌ リリース作成エラー: {e}")

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHubクイックコマンド")
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # commit-push
    cp_parser = subparsers.add_parser("commit-push", help="コミット・プッシュ")
    cp_parser.add_argument("-m", "--message", help="コミットメッセージ")
    
    # status
    subparsers.add_parser("status", help="ステータス確認")
    
    # issue
    issue_parser = subparsers.add_parser("issue", help="イシュー作成")
    issue_parser.add_argument("title", help="タイトル")
    issue_parser.add_argument("-b", "--body", help="本文")
    issue_parser.add_argument("-l", "--labels", help="ラベル（カンマ区切り）")
    
    # release
    release_parser = subparsers.add_parser("release", help="リリース作成")
    release_parser.add_argument("tag", help="タグ名（例: v1.0.0）")
    release_parser.add_argument("-t", "--title", help="タイトル")
    
    args = parser.parse_args()
    
    if args.command == "commit-push":
        quick_commit_push(args.message)
    elif args.command == "status":
        quick_status()
    elif args.command == "issue":
        quick_issue(args.title, args.body, args.labels)
    elif args.command == "release":
        quick_release(args.tag, args.title)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()






















