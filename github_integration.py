"""
GitHub統合モジュール（改善版）
GitHub APIを使用してリポジトリ情報を取得・操作
ベースクラスを使用して統一モジュールを活用
"""

import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# .envファイルの読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenvがインストールされていない場合はスキップ

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
    
    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        GitHubリポジトリを作成
        
        Args:
            name: リポジトリ名
            description: 説明
            private: プライベートかどうか
            auto_init: READMEで自動初期化するかどうか
        
        Returns:
            作成されたリポジトリ情報の辞書
        """
        if not self.is_available():
            return None
        
        try:
            user = self.github.get_user()
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init
            )
            
            result = {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "private": repo.private
            }
            
            self.logger.info(f"リポジトリ作成完了: {repo.full_name}")
            return result
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"name": name, "action": "create_repository"},
                user_message="リポジトリの作成に失敗しました"
            )
            self.logger.error(f"リポジトリ作成エラー: {error.message}")
            return None
    
    def get_commits(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        コミット履歴を取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            branch: ブランチ名
            limit: 取得数
        
        Returns:
            コミット情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            commits = repo_obj.get_commits(sha=branch)
            
            results = []
            for commit in list(commits)[:limit]:
                results.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name if commit.commit.author else None,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "url": commit.html_url
                })
            
            self.logger.info(f"コミット履歴取得完了: {len(results)}件")
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"owner": owner, "repo": repo, "branch": branch, "action": "get_commits"},
                user_message="コミット履歴の取得に失敗しました"
            )
            self.logger.error(f"コミット履歴取得エラー: {error.message}")
            return []
    
    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        プルリクエストを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            state: 状態（open, closed, all）
            limit: 取得数
        
        Returns:
            プルリクエスト情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            prs = repo_obj.get_pulls(state=state)
            
            results = []
            for pr in list(prs)[:limit]:
                results.append({
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "author": pr.user.login if pr.user else None,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "url": pr.html_url
                })
            
            self.logger.info(f"プルリクエスト取得完了: {len(results)}件")
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"owner": owner, "repo": repo, "state": state, "action": "get_pull_requests"},
                user_message="プルリクエストの取得に失敗しました"
            )
            self.logger.error(f"プルリクエスト取得エラー: {error.message}")
            return []
    
    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        イシューを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            state: 状態（open, closed, all）
            limit: 取得数
        
        Returns:
            イシュー情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            issues = repo_obj.get_issues(state=state)
            
            results = []
            for issue in list(issues)[:limit]:
                results.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "state": issue.state,
                    "author": issue.user.login if issue.user else None,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "labels": [label.name for label in issue.labels],
                    "url": issue.html_url
                })
            
            self.logger.info(f"イシュー取得完了: {len(results)}件")
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"owner": owner, "repo": repo, "state": state, "action": "get_issues"},
                user_message="イシューの取得に失敗しました"
            )
            self.logger.error(f"イシュー取得エラー: {error.message}")
            return []
    
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        イシューを作成
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            title: タイトル
            body: 本文
            labels: ラベルリスト
        
        Returns:
            作成されたイシュー情報の辞書
        """
        if not self.is_available():
            return None
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            issue = repo_obj.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )
            
            result = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "url": issue.html_url
            }
            
            self.logger.info(f"イシュー作成完了: #{issue.number}")
            return result
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"owner": owner, "repo": repo, "title": title, "action": "create_issue"},
                user_message="イシューの作成に失敗しました"
            )
            self.logger.error(f"イシュー作成エラー: {error.message}")
            return None

