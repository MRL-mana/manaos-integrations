#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub活用の使用例
"""

import sys
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from github_integration import GitHubIntegration
from github_automation import GitHubAutomation
from github_helper import GitHubHelper


def example_repository_info():
    """リポジトリ情報取得の例"""
    print("=" * 60)
    print("例1: リポジトリ情報の取得")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません（GITHUB_TOKENを設定してください）")
        return
    
    # リポジトリ情報を取得
    repo_info = github.get_repository("comfyanonymous", "ComfyUI")
    
    if repo_info:
        print(f"リポジトリ名: {repo_info['name']}")
        print(f"説明: {repo_info['description']}")
        print(f"スター数: {repo_info['stars']}")
        print(f"フォーク数: {repo_info['forks']}")
        print(f"言語: {repo_info['language']}")
        print(f"URL: {repo_info['url']}")


def example_search_repositories():
    """リポジトリ検索の例"""
    print("\n" + "=" * 60)
    print("例2: リポジトリの検索")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    # リポジトリを検索
    repos = github.search_repositories(
        query="python ai framework",
        sort="stars",
        order="desc",
        per_page=5
    )
    
    print(f"検索結果: {len(repos)}件\n")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo['full_name']}")
        print(f"   説明: {repo['description']}")
        print(f"   スター数: {repo['stars']}")
        print(f"   URL: {repo['url']}\n")


def example_auto_commit():
    """自動コミットの例"""
    print("=" * 60)
    print("例3: 自動コミット・プッシュ")
    print("=" * 60)
    
    helper = GitHubHelper()
    
    # Gitリポジトリの状態を確認
    if not (helper.repo_path / ".git").exists():
        print("⚠️ Gitリポジトリが初期化されていません")
        print("   まず、git init を実行してください")
        return
    
    # 自動コミット
    success = helper.auto_commit(
        message="例: GitHub統合のテスト",
        exclude_patterns=["*.log", "*.db", "__pycache__/"]
    )
    
    if success:
        print("✅ コミット成功")
        
        # プッシュ（リモートが設定されている場合）
        # helper.auto_push()
    else:
        print("⚠️ コミットする変更がありませんでした")


def example_create_repository():
    """リポジトリ作成の例"""
    print("\n" + "=" * 60)
    print("例4: GitHubリポジトリの作成と接続")
    print("=" * 60)
    
    automation = GitHubAutomation()
    
    if not automation.github or not automation.github.is_available():
        print("❌ GitHub統合が利用できません（GITHUB_TOKENを設定してください）")
        return
    
    # 注意: 実際にリポジトリを作成する場合は、以下のコメントを外してください
    # remote_url = automation.create_and_connect_repo(
    #     repo_name="test-repo",
    #     description="テスト用リポジトリ",
    #     private=False
    # )
    # 
    # if remote_url:
    #     print(f"✅ リポジトリ作成完了: {remote_url}")
    
    print("⚠️ 実際にリポジトリを作成するには、コードのコメントを外してください")


def example_get_issues():
    """イシュー取得の例"""
    print("\n" + "=" * 60)
    print("例5: イシューの取得")
    print("=" * 60)
    
    github = GitHubIntegration()
    
    if not github.is_available():
        print("❌ GitHub統合が利用できません")
        return
    
    # イシューを取得（例: ComfyUIリポジトリ）
    issues = github.get_issues(
        owner="comfyanonymous",
        repo="ComfyUI",
        state="open",
        limit=5
    )
    
    print(f"オープンなイシュー: {len(issues)}件\n")
    for issue in issues:
        print(f"#{issue['number']}: {issue['title']}")
        print(f"   作成者: {issue['author']}")
        print(f"   ラベル: {', '.join(issue['labels'])}")
        print(f"   URL: {issue['url']}\n")


def main():
    """メイン関数"""
    print("GitHub活用の使用例")
    print("=" * 60)
    print()
    
    # 例1: リポジトリ情報取得
    example_repository_info()
    
    # 例2: リポジトリ検索
    example_search_repositories()
    
    # 例3: 自動コミット
    example_auto_commit()
    
    # 例4: リポジトリ作成（コメントアウト）
    example_create_repository()
    
    # 例5: イシュー取得
    example_get_issues()
    
    print("\n" + "=" * 60)
    print("使用例の実行が完了しました")
    print("詳細は GITHUB_USAGE_GUIDE.md を参照してください")
    print("=" * 60)


if __name__ == "__main__":
    main()

