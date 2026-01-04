#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
リポジトリセットアップの確認スクリプト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_integration import GitHubIntegration
import subprocess

def main():
    print("=" * 60)
    print("リポジトリセットアップ確認")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("\n❌ GitHub統合が利用できません")
        return
    
    print("\n✅ GitHub統合: 利用可能")
    
    # リポジトリ情報を取得
    print("\nリポジトリ情報を取得中...")
    repo_info = github.get_repository("MRL-mana", "manaos-integrations")
    
    if repo_info:
        print(f"\n📦 リポジトリ情報:")
        print(f"  名前: {repo_info['name']}")
        print(f"  説明: {repo_info['description']}")
        print(f"  プライベート: {'✅ はい' if repo_info.get('private') else '❌ いいえ（公開されています！）'}")
        print(f"  スター数: {repo_info['stars']}")
        print(f"  フォーク数: {repo_info['forks']}")
        print(f"  URL: {repo_info['url']}")
        
        if not repo_info.get('private'):
            print("\n⚠️ 警告: このリポジトリは公開されています！")
            print("プライベートに変更してください:")
            print(f"   {repo_info['url']}/settings")
    else:
        print("❌ リポジトリ情報の取得に失敗しました")
        return
    
    # リモート設定を確認
    print("\n📡 リモート設定:")
    result = subprocess.run(
        ["git", "remote", "-v"],
        capture_output=True,
        text=True,
        check=True
    )
    print(result.stdout)
    
    # ブランチ情報を確認
    print("🌿 ブランチ情報:")
    result = subprocess.run(
        ["git", "branch", "-vv"],
        capture_output=True,
        text=True,
        check=True
    )
    print(result.stdout)
    
    # .gitignoreの確認
    print("🔒 セキュリティ確認:")
    result = subprocess.run(
        ["git", "check-ignore", "-v", ".env"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode == 0:
        print("  ✅ .envファイルは.gitignoreで除外されています")
    else:
        print("  ⚠️ .envファイルが.gitignoreに含まれていません")
    
    print("\n" + "=" * 60)
    if repo_info.get('private'):
        print("✅ セットアップ完了！プライベートリポジトリとして管理されています")
    else:
        print("⚠️ リポジトリをプライベートに変更してください")
    print("=" * 60)

if __name__ == "__main__":
    main()

