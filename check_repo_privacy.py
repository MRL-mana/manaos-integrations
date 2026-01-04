#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
リポジトリのプライバシー設定を確認・変更するスクリプト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_integration import GitHubIntegration

def main():
    print("=" * 60)
    print("リポジトリプライバシー設定確認")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    print("✅ GitHub統合: 利用可能")
    
    # ユーザー名を取得
    try:
        user = github.github.get_user()
        username = user.login
        print(f"\nGitHubユーザー: {username}")
    except Exception as e:
        print(f"❌ ユーザー情報の取得に失敗: {e}")
        return
    
    # リポジトリ名を入力
    repo_name = input(f"\nリポジトリ名を入力してください (デフォルト: manaos-integrations): ").strip()
    if not repo_name:
        repo_name = "manaos-integrations"
    
    # リポジトリ情報を取得
    print("\nリポジトリ情報を取得中...")
    repo_info = github.get_repository(username, repo_name)
    
    if not repo_info:
        print(f"❌ リポジトリ '{username}/{repo_name}' が見つかりません")
        print("\nリポジトリを作成する場合は:")
        print("  python setup_github_repo.py")
        print("  （プライベートリポジトリとして作成されます）")
        return
    
    print(f"\n📦 リポジトリ情報:")
    print(f"  名前: {repo_info['name']}")
    print(f"  説明: {repo_info['description']}")
    print(f"  プライベート: {'はい' if repo_info.get('private') else 'いいえ'}")
    print(f"  URL: {repo_info['url']}")
    
    # プライベートでない場合の警告
    if not repo_info.get('private'):
        print("\n⚠️ 警告: このリポジトリは公開されています！")
        print("\nプライベートに変更するには:")
        print("1. GitHubのリポジトリページにアクセス")
        print(f"   {repo_info['url']}")
        print("2. Settings → General → Danger Zone")
        print("3. 'Change repository visibility' → 'Change to private'")
        print("\nまたは、新しいプライベートリポジトリを作成:")
        print("  python setup_github_repo.py")
    else:
        print("\n✅ リポジトリはプライベートに設定されています")

if __name__ == "__main__":
    main()

