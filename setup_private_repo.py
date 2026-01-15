#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プライベートGitHubリポジトリのセットアップ
既存リポジトリに接続、または手動作成を案内
"""

import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_integration import GitHubIntegration
from github_helper import GitHubHelper

def main():
    print("=" * 60)
    print("プライベートGitHubリポジトリセットアップ")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("\n❌ GitHub統合が利用できません")
        print("   GITHUB_TOKENを.envファイルに設定してください")
        return
    
    print("\n✅ GitHub統合: 利用可能")
    
    # ユーザー名を取得
    try:
        user = github.github.get_user()
        username = user.login
        print(f"\nGitHubユーザー: {username}")
    except Exception as e:
        print(f"❌ ユーザー情報の取得に失敗: {e}")
        return
    
    repo_name = "manaos-integrations"
    repo_path = Path.cwd()
    
    print(f"\nリポジトリ名: {repo_name}")
    print(f"作業ディレクトリ: {repo_path}")
    
    # 既存のリポートを確認
    result = subprocess.run(
        ["git", "remote", "-v"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False
    )
    
    has_remote = bool(result.stdout.strip())
    
    if has_remote:
        print(f"\n既存のリモート設定:")
        print(result.stdout)
        print("\n既存のリモートを使用しますか？ (y/n): ", end="")
        choice = input().strip().lower()
        if choice == 'y':
            print("\n既存のリモートを使用します")
            # プッシュを試みる
            helper = GitHubHelper()
            print("\n変更をプッシュ中...")
            if helper.auto_push():
                print("✅ プッシュ完了")
            else:
                print("⚠️ プッシュに失敗しました")
            return
    
    # リポジトリが存在するか確認
    print(f"\nリポジトリ '{username}/{repo_name}' の存在を確認中...")
    repo_info = github.get_repository(username, repo_name)
    
    if repo_info:
        print(f"✅ リポジトリが見つかりました")
        print(f"   プライベート: {'はい' if repo_info.get('private') else 'いいえ'}")
        
        if not repo_info.get('private'):
            print("\n⚠️ 警告: このリポジトリは公開されています！")
            print("プライベートに変更してください:")
            print(f"   {repo_info['url']}/settings")
            print("   Settings → General → Danger Zone → Change to private")
            return
        
        # リモートを設定
        remote_url = f"https://github.com/{username}/{repo_name}.git"
        print(f"\nリモートを設定中: {remote_url}")
        
        if has_remote:
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=repo_path,
                check=True
            )
            print("✅ リモートURLを更新しました")
        else:
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=repo_path,
                check=True
            )
            print("✅ リモートを追加しました")
        
        # コミット・プッシュ
        helper = GitHubHelper()
        print("\n変更をコミット中...")
        if helper.auto_commit("GitHub統合機能追加"):
            print("✅ コミット完了")
            
            print("\n変更をプッシュ中...")
            if helper.auto_push():
                print("✅ プッシュ完了")
                print(f"\n🎉 GitHubリポジトリへの接続が完了しました！")
                print(f"   URL: {repo_info['url']}")
            else:
                print("⚠️ プッシュに失敗しました")
        else:
            print("⚠️ コミットする変更がありませんでした")
            print(f"\n既存のコミットをプッシュする場合は:")
            print(f"  git push -u origin master")
    
    else:
        print(f"❌ リポジトリ '{username}/{repo_name}' が見つかりません")
        print("\n以下の方法でリポジトリを作成してください:")
        print("\n【方法1】GitHubで手動作成（推奨）:")
        print("1. https://github.com/new にアクセス")
        print(f"2. リポジトリ名: {repo_name}")
        print("3. 説明: ManaOS外部システム統合モジュール集")
        print("4. ⚠️ 必ず「Private」を選択")
        print("5. 「Create repository」をクリック")
        print("\n作成後、このスクリプトを再度実行してください")
        print("\n【方法2】GitHub CLIを使用:")
        print(f"  gh repo create {repo_name} --private --description 'ManaOS外部システム統合モジュール集'")
        print("\n【方法3】APIで作成（repoスコープが必要）:")
        print("  トークンにrepoスコープを追加してから:")
        print("  python setup_github_repo.py")

if __name__ == "__main__":
    main()






















