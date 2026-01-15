#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub活用ワークフロー
日常的なGitHub操作を簡単にするスクリプト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_integration import GitHubIntegration
from github_helper import GitHubHelper
from datetime import datetime

def show_menu():
    """メニューを表示"""
    print("\n" + "=" * 60)
    print("GitHub活用メニュー")
    print("=" * 60)
    print("1. 変更をコミット・プッシュ")
    print("2. GitHubと同期（プル→コミット→プッシュ）")
    print("3. リポジトリ情報を表示")
    print("4. イシュー一覧を表示")
    print("5. イシューを作成")
    print("6. コミット履歴を表示")
    print("7. リポジトリ検索")
    print("0. 終了")
    print("=" * 60)

def commit_and_push():
    """変更をコミット・プッシュ"""
    helper = GitHubHelper()
    
    message = input("コミットメッセージを入力: ").strip()
    if not message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"更新: {timestamp}"
    
    if helper.auto_commit(message):
        print("✅ コミット完了")
        if helper.auto_push():
            print("✅ プッシュ完了")
        else:
            print("⚠️ プッシュに失敗しました")
    else:
        print("⚠️ コミットする変更がありませんでした")

def sync_with_github():
    """GitHubと同期"""
    helper = GitHubHelper()
    
    owner = input("リポジトリオーナー (デフォルト: MRL-mana): ").strip() or "MRL-mana"
    repo = input("リポジトリ名 (デフォルト: manaos-integrations): ").strip() or "manaos-integrations"
    branch = input("ブランチ名 (デフォルト: main): ").strip() or "main"
    
    print("\n同期中...")
    result = helper.sync_with_github(owner, repo, branch)
    
    print(f"\n結果:")
    print(f"  プル: {'成功' if result['pull'] else '失敗'}")
    print(f"  コミット: {'成功' if result['commit'] else '失敗'}")
    print(f"  プッシュ: {'成功' if result['push'] else '失敗'}")
    
    if result['errors']:
        print(f"\nエラー:")
        for error in result['errors']:
            print(f"  - {error}")

def show_repo_info():
    """リポジトリ情報を表示"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    owner = input("リポジトリオーナー (デフォルト: comfyanonymous): ").strip() or "comfyanonymous"
    repo = input("リポジトリ名 (デフォルト: ComfyUI): ").strip() or "ComfyUI"
    
    print("\n取得中...")
    repo_info = github.get_repository(owner, repo)
    
    if repo_info:
        print(f"\n📦 リポジトリ情報:")
        print(f"  名前: {repo_info['name']}")
        print(f"  説明: {repo_info['description']}")
        print(f"  スター数: {repo_info['stars']:,}")
        print(f"  フォーク数: {repo_info['forks']:,}")
        print(f"  言語: {repo_info['language']}")
        print(f"  URL: {repo_info['url']}")
    else:
        print("❌ リポジトリ情報の取得に失敗しました")

def show_issues():
    """イシュー一覧を表示"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    owner = input("リポジトリオーナー (デフォルト: comfyanonymous): ").strip() or "comfyanonymous"
    repo = input("リポジトリ名 (デフォルト: ComfyUI): ").strip() or "ComfyUI"
    state = input("状態 (open/closed/all, デフォルト: open): ").strip() or "open"
    limit = int(input("表示数 (デフォルト: 10): ").strip() or "10")
    
    print("\n取得中...")
    issues = github.get_issues(owner, repo, state, limit)
    
    if issues:
        print(f"\n📋 イシュー一覧 ({len(issues)}件):")
        for issue in issues:
            print(f"\n  #{issue['number']}: {issue['title']}")
            print(f"    状態: {issue['state']}")
            print(f"    作成者: {issue['author']}")
            if issue['labels']:
                print(f"    ラベル: {', '.join(issue['labels'])}")
            print(f"    URL: {issue['url']}")
    else:
        print("イシューが見つかりませんでした")

def create_issue():
    """イシューを作成"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    owner = input("リポジトリオーナー: ").strip()
    repo = input("リポジトリ名: ").strip()
    title = input("タイトル: ").strip()
    body = input("本文 (Enterで空): ").strip()
    labels_input = input("ラベル (カンマ区切り, Enterで空): ").strip()
    labels = [l.strip() for l in labels_input.split(",")] if labels_input else []
    
    print("\n作成中...")
    issue = github.create_issue(owner, repo, title, body, labels)
    
    if issue:
        print(f"\n✅ イシューを作成しました:")
        print(f"  #{issue['number']}: {issue['title']}")
        print(f"  URL: {issue['url']}")
    else:
        print("❌ イシューの作成に失敗しました")

def show_commits():
    """コミット履歴を表示"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    owner = input("リポジトリオーナー (デフォルト: comfyanonymous): ").strip() or "comfyanonymous"
    repo = input("リポジトリ名 (デフォルト: ComfyUI): ").strip() or "ComfyUI"
    branch = input("ブランチ名 (デフォルト: main): ").strip() or "main"
    limit = int(input("表示数 (デフォルト: 10): ").strip() or "10")
    
    print("\n取得中...")
    commits = github.get_commits(owner, repo, branch, limit)
    
    if commits:
        print(f"\n📝 コミット履歴 ({len(commits)}件):")
        for commit in commits:
            print(f"\n  {commit['sha'][:7]}: {commit['message'].split(chr(10))[0]}")
            print(f"    作成者: {commit['author']}")
            print(f"    日時: {commit['date']}")
            print(f"    URL: {commit['url']}")
    else:
        print("コミットが見つかりませんでした")

def search_repositories():
    """リポジトリを検索"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    query = input("検索クエリ: ").strip()
    if not query:
        query = "python ai"
    
    limit = int(input("表示数 (デフォルト: 10): ").strip() or "10")
    
    print("\n検索中...")
    repos = github.search_repositories(query, per_page=limit)
    
    if repos:
        print(f"\n🔍 検索結果 ({len(repos)}件):")
        for i, repo in enumerate(repos, 1):
            print(f"\n  {i}. {repo['full_name']}")
            print(f"     説明: {repo['description']}")
            print(f"     スター数: {repo['stars']:,}")
            print(f"     URL: {repo['url']}")
    else:
        print("リポジトリが見つかりませんでした")

def main():
    """メイン関数"""
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        print("   GITHUB_TOKENを.envファイルに設定してください")
        return
    
    print("✅ GitHub統合: 利用可能")
    
    while True:
        show_menu()
        choice = input("\n選択してください: ").strip()
        
        if choice == "1":
            commit_and_push()
        elif choice == "2":
            sync_with_github()
        elif choice == "3":
            show_repo_info()
        elif choice == "4":
            show_issues()
        elif choice == "5":
            create_issue()
        elif choice == "6":
            show_commits()
        elif choice == "7":
            search_repositories()
        elif choice == "0":
            print("終了します")
            break
        else:
            print("無効な選択です")

if __name__ == "__main__":
    main()






















