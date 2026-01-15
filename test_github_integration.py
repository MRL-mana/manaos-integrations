#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub統合テストスクリプト
"""

import os
import sys

# GitHubトークンは環境変数で指定してください（値の直書きは禁止）
if not os.environ.get("GITHUB_TOKEN"):
    print(
        "⚠️ GITHUB_TOKEN が未設定です。環境変数に設定してから実行してください。",
        file=sys.stderr,
    )

from github_integration import GitHubIntegration
from manaos_complete_integration import ManaOSCompleteIntegration

def test_github_integration():
    """GitHub統合をテスト"""
    print("=" * 60)
    print("GitHub統合テスト")
    print("=" * 60)
    
    # GitHub統合をテスト
    print("\n[1] GitHub統合のテスト")
    print("-" * 60)
    gh = GitHubIntegration()
    print(f"GitHub Available: {gh.is_available()}")
    
    if gh.is_available():
        # リポジトリ情報を取得
        print("\n[2] リポジトリ情報の取得")
        print("-" * 60)
        repo = gh.get_repository("comfyanonymous", "ComfyUI")
        if repo:
            print(f"リポジトリ名: {repo['name']}")
            print(f"説明: {repo['description']}")
            print(f"スター数: {repo['stars']}")
            print(f"フォーク数: {repo['forks']}")
            print(f"言語: {repo['language']}")
            print(f"URL: {repo['url']}")
        
        # リポジトリを検索
        print("\n[3] リポジトリ検索")
        print("-" * 60)
        repos = gh.search_repositories("python ai", per_page=5)
        print(f"検索結果: {len(repos)}件")
        for i, r in enumerate(repos[:3], 1):
            print(f"{i}. {r['full_name']} - {r['stars']} stars")
    else:
        print("⚠️ GitHub統合が利用できません")
    
    # 完全統合システムから確認
    print("\n[4] 完全統合システムからの確認")
    print("-" * 60)
    integration = ManaOSCompleteIntegration()
    status = integration.get_complete_status()
    gh_status = status.get("github", {})
    print(f"GitHub Status: {gh_status}")
    
    if gh_status.get("github_integration", {}).get("available"):
        print("✅ GitHub統合が正常に動作しています！")
    else:
        print("⚠️ GitHub統合が利用できません")

if __name__ == "__main__":
    test_github_integration()






















