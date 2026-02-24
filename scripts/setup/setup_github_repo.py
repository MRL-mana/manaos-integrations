#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHubリポジトリのセットアップスクリプト
リポジトリ作成、接続、初回プッシュまで自動化
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_automation import GitHubAutomation
from github_helper import GitHubHelper

def main():
    print("=" * 60)
    print("GitHubリポジトリセットアップ")
    print("=" * 60)
    
    automation = GitHubAutomation()
    
    # 現在の状態を確認
    status = automation.get_status()
    print(f"\n現在の状態:")
    print(f"  Gitリポジトリ: {'初期化済み' if status['is_git_repo'] else '未初期化'}")
    print(f"  リモート設定: {'あり' if status['has_remote'] else 'なし'}")
    print(f"  現在のブランチ: {status['current_branch'] or 'なし'}")
    print(f"  未コミットの変更: {'あり' if status['uncommitted_changes'] else 'なし'}")
    
    # GitHub統合が利用可能か確認
    if not automation.github or not automation.github.is_available():
        print("\n❌ GitHub統合が利用できません")
        print("   GITHUB_TOKENを.envファイルに設定してください")
        return
    
    print("\n✅ GitHub統合: 利用可能")
    
    # リポジトリ名を決定
    repo_name = "manaos-integrations"
    print(f"\nリポジトリ名: {repo_name}")
    
    # リポジトリを作成して接続（プライベート）
    print("\nリポジトリを作成中（プライベート）...")
    remote_url = automation.create_and_connect_repo(
        repo_name=repo_name,
        description="ManaOS外部システム統合モジュール集",
        private=True  # プライベートリポジトリとして作成
    )
    
    if not remote_url:
        print("❌ リポジトリの作成に失敗しました")
        return
    
    print(f"✅ リポジトリ作成完了: {remote_url}")
    
    # 初回コミット・プッシュ
    helper = GitHubHelper()
    
    print("\n変更をコミット中...")
    if helper.auto_commit("初期コミット: ManaOS統合モジュール"):
        print("✅ コミット完了")
        
        print("\n変更をプッシュ中...")
        if helper.auto_push("main"):
            print("✅ プッシュ完了")
            print(f"\n🎉 GitHubリポジトリのセットアップが完了しました！")
            print(f"   URL: https://github.com/MRL-mana/{repo_name}")
        else:
            print("⚠️ プッシュに失敗しました（リモートが設定されていない可能性があります）")
    else:
        print("⚠️ コミットする変更がありませんでした")

if __name__ == "__main__":
    main()

