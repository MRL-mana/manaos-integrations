"""
GitHub統合モジュール（改善版）
GitHub APIを使用してリポジトリ情報を取得・操作
ベースクラスを使用して統一モジュールを活用
"""

import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from github import Github
    GITHUB_PY_AVAILABLE = True
except ImportError:
    GITHUB_PY_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration


class GitHubIntegration(BaseIntegration):
    """GitHub統合クラス（改善版）"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初期化
        
        Args:
            token: GitHub Personal Access Token（Noneの場合は環境変数から取得）
        """
        super().__init__("GitHub")
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.github = None
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not GITHUB_PY_AVAILABLE:
            self.logger.warning("PyGithubライブラリがインストールされていません")
            return False
        
        if not self.token:
            self.logger.warning("GitHubトークンが設定されていません")
            return False
        
        try:
            self.github = Github(self.token)
            # 接続テスト
            self.github.get_user().login
            self.logger.info("GitHub統合を初期化しました")
            return True
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"action": "initialize"},
                user_message="GitHub統合の初期化に失敗しました"
            )
            self.logger.error(f"GitHub統合の初期化エラー: {error.message}")
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return GITHUB_PY_AVAILABLE and self.github is not None
    
    def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        リポジトリ情報を取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
        
        Returns:
            リポジトリ情報の辞書
        """
        if not self.is_available():
            return None
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            return {
                "name": repo_obj.name,
                "full_name": repo_obj.full_name,
                "description": repo_obj.description,
                "stars": repo_obj.stargazers_count,
                "forks": repo_obj.forks_count,
                "language": repo_obj.language,
                "url": repo_obj.html_url,
                "created_at": repo_obj.created_at.isoformat() if repo_obj.created_at else None,
                "updated_at": repo_obj.updated_at.isoformat() if repo_obj.updated_at else None
            }
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"owner": owner, "repo": repo, "action": "get_repository"},
                user_message="リポジトリ情報の取得に失敗しました"
            )
            self.logger.error(f"リポジトリ情報取得エラー: {error.message}")
            return None
    
    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """
        リポジトリを検索
        
        Args:
            query: 検索クエリ
            sort: ソート方法（stars, forks, updated等）
            order: 順序（asc, desc）
            per_page: 1ページあたりの取得数
        
        Returns:
            リポジトリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repos = self.github.search_repositories(
                query=query,
                sort=sort,
                order=order
            )
            
            results = []
            for repo in repos[:per_page]:
                results.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                    "url": repo.html_url
                })
            
            self.logger.info(f"リポジトリ検索完了: {len(results)}件")
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"query": query, "action": "search_repositories"},
                user_message="リポジトリの検索に失敗しました"
            )
            self.logger.error(f"リポジトリ検索エラー: {error.message}")
            return []
    
    def get_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """
        ユーザーのリポジトリ一覧を取得
        
        Args:
            username: ユーザー名
        
        Returns:
            リポジトリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            user = self.github.get_user(username)
            repos = user.get_repos()
            
            results = []
            for repo in repos:
                results.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                    "url": repo.html_url
                })
            
            self.logger.info(f"ユーザーリポジトリ取得完了: {len(results)}件")
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"username": username, "action": "get_user_repositories"},
                user_message="ユーザーリポジトリの取得に失敗しました"
            )
            self.logger.error(f"ユーザーリポジトリ取得エラー: {error.message}")
            return []






















