#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub自動化スクリプト
リポジトリ作成、コミット、プッシュなどの自動化機能
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from github_integration import GitHubIntegration
    GITHUB_INTEGRATION_AVAILABLE = True
except ImportError:
    GITHUB_INTEGRATION_AVAILABLE = False


class GitHubAutomation:
    """GitHub自動化クラス"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初期化
        
        Args:
            token: GitHub Personal Access Token
        """
        self.github = None
        if GITHUB_INTEGRATION_AVAILABLE:
            self.github = GitHubIntegration(token)
            if not self.github.is_available():
                self.github = None
        
        self.repo_path = Path.cwd()
    
    def initialize_repo(self, remote_url: Optional[str] = None) -> bool:
        """
        Gitリポジトリを初期化（既に初期化済みの場合はスキップ）
        
        Args:
            remote_url: リモートリポジトリURL（オプション）
        
        Returns:
            成功かどうか
        """
        try:
            # 既にGitリポジトリかチェック
            if (self.repo_path / ".git").exists():
                print("✅ Gitリポジトリは既に初期化済みです")
                if remote_url:
                    # リモートを追加または更新
                    subprocess.run(
                        ["git", "remote", "set-url", "origin", remote_url],
                        cwd=self.repo_path,
                        check=False
                    )
                    subprocess.run(
                        ["git", "remote", "add", "origin", remote_url],
                        cwd=self.repo_path,
                        check=False
                    )
                return True
            
            # Gitリポジトリを初期化
            subprocess.run(["git", "init"], cwd=self.repo_path, check=True)
            print("✅ Gitリポジトリを初期化しました")
            
            # リモートを追加
            if remote_url:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote_url],
                    cwd=self.repo_path,
                    check=True
                )
                print(f"✅ リモートリポジトリを追加: {remote_url}")
            
            return True
            
        except Exception as e:
            print(f"❌ Gitリポジトリ初期化エラー: {e}")
            return False
    
    def create_and_connect_repo(
        self,
        repo_name: str,
        description: Optional[str] = None,
        private: bool = False
    ) -> Optional[str]:
        """
        GitHubリポジトリを作成して接続
        
        Args:
            repo_name: リポジトリ名
            description: 説明
            private: プライベートかどうか
        
        Returns:
            リモートURL（失敗時はNone）
        """
        if not self.github or not self.github.is_available():
            print("❌ GitHub統合が利用できません")
            return None
        
        try:
            # リポジトリを作成
            repo_info = self.github.create_repository(
                name=repo_name,
                description=description,
                private=private,
                auto_init=False
            )
            
            if not repo_info:
                print("❌ リポジトリの作成に失敗しました")
                return None
            
            remote_url = repo_info["clone_url"]
            print(f"✅ GitHubリポジトリを作成: {repo_info['full_name']}")
            print(f"    URL: {repo_info['url']}")
            
            # Gitリポジトリを初期化して接続
            self.initialize_repo(remote_url)
            
            return remote_url
            
        except Exception as e:
            print(f"❌ リポジトリ作成エラー: {e}")
            return None
    
    def commit_and_push(
        self,
        message: str,
        branch: str = "main",
        files: Optional[List[str]] = None
    ) -> bool:
        """
        変更をコミットしてプッシュ
        
        Args:
            message: コミットメッセージ
            branch: ブランチ名
            files: コミットするファイルリスト（Noneの場合はすべて）
        
        Returns:
            成功かどうか
        """
        try:
            # ブランチを作成またはチェックアウト
            subprocess.run(
                ["git", "checkout", "-b", branch],
                cwd=self.repo_path,
                check=False
            )
            
            # ファイルを追加
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        cwd=self.repo_path,
                        check=True
                    )
            else:
                subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            
            # コミット
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True
            )
            print(f"✅ コミット完了: {message}")
            
            # プッシュ
            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=self.repo_path,
                check=True
            )
            print(f"✅ プッシュ完了: {branch}")
            
            return True
            
        except Exception as e:
            print(f"❌ コミット・プッシュエラー: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Gitリポジトリの状態を取得
        
        Returns:
            状態情報の辞書
        """
        status = {
            "is_git_repo": (self.repo_path / ".git").exists(),
            "has_remote": False,
            "current_branch": None,
            "uncommitted_changes": False
        }
        
        if not status["is_git_repo"]:
            return status
        
        try:
            # リモートの確認
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            status["has_remote"] = bool(result.stdout.strip())
            
            # 現在のブランチ
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            status["current_branch"] = result.stdout.strip() or "main"
            
            # 未コミットの変更
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            status["uncommitted_changes"] = bool(result.stdout.strip())
            
        except Exception as e:
            print(f"⚠️ 状態取得エラー: {e}")
        
        return status


def main():
    """メイン関数"""
    print("GitHub自動化スクリプト")
    print("=" * 60)
    
    automation = GitHubAutomation()
    
    # 状態を確認
    status = automation.get_status()
    print(f"\n📊 Gitリポジトリ状態:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # GitHub統合の状態
    if automation.github and automation.github.is_available():
        print("\n✅ GitHub統合: 利用可能")
    else:
        print("\n⚠️ GitHub統合: 利用不可（GITHUB_TOKENを設定してください）")


if __name__ == "__main__":
    main()






















