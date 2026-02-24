#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のGitHubリポジトリに接続するスクリプト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_automation import GitHubAutomation
from github_helper import GitHubHelper
import subprocess

def main():
    print("=" * 60)
    print("既存のGitHubリポジトリに接続")
    print("=" * 60)
    
    automation = GitHubAutomation()
    
    # GitHub統合が利用可能か確認
    if not automation.github or not automation.github.is_available():
        print("\n❌ GitHub統合が利用できません")
        return
    
    print("\n✅ GitHub統合: 利用可能")
    
    # ユーザー名を取得
    try:
        user = automation.github.github.get_user()
        username = user.login
        print(f"\nGitHubユーザー: {username}")
    except Exception as e:
        print(f"❌ ユーザー情報の取得に失敗: {e}")
        return
    
    # リポジトリ名を入力
    repo_name = input(f"\nリポジトリ名を入力してください (デフォルト: manaos-integrations): ").strip()
    if not repo_name:
        repo_name = "manaos-integrations"
    
    # リモートURLを構築
    remote_url = f"https://github.com/{username}/{repo_name}.git"
    
    print(f"\nリモートURL: {remote_url}")
    print("⚠️ 注意: プライベートリポジトリとして設定してください")
    confirm = input("このリポジトリに接続しますか？ (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("キャンセルしました")
        return
    
    # リモートを設定
    repo_path = Path.cwd()
    
    try:
        # 既存のリモートを確認
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )
        
        if "origin" in result.stdout:
            # 既存のoriginを更新
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=repo_path,
                check=True
            )
            print("✅ リモートURLを更新しました")
        else:
            # 新しいリモートを追加
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=repo_path,
                check=True
            )
            print("✅ リモートを追加しました")
        
        # 現在のブランチを確認
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = result.stdout.strip() or "master"
        
        print(f"\n現在のブランチ: {current_branch}")
        
        # 変更をコミット
        helper = GitHubHelper()
        print("\n変更をコミット中...")
        if helper.auto_commit("GitHub統合機能追加"):
            print("✅ コミット完了")
            
            # プッシュ
            print("\n変更をプッシュ中...")
            if helper.auto_push(current_branch):
                print("✅ プッシュ完了")
                print(f"\n🎉 GitHubリポジトリへの接続が完了しました！")
                print(f"   URL: https://github.com/{username}/{repo_name}")
            else:
                print("⚠️ プッシュに失敗しました")
                print("   リポジトリが存在するか、権限を確認してください")
        else:
            print("⚠️ コミットする変更がありませんでした")
            print(f"\n既存のコミットをプッシュする場合は:")
            print(f"  git push -u origin {current_branch}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()

