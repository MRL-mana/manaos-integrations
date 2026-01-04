"""
GitHub統合モジュール
GitHub APIを使用してリポジトリ情報を取得・操作
"""

import os
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from github import Github
    GITHUB_PY_AVAILABLE = True
except ImportError:
    GITHUB_PY_AVAILABLE = False
    logger.warning("PyGithubライブラリがインストールされていません。pip install PyGithub")


class GitHubIntegration:
    """GitHub統合クラス"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初期化
        
        Args:
            token: GitHub Personal Access Token（Noneの場合は環境変数から取得）
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.github = None
        
        if GITHUB_PY_AVAILABLE and self.token:
            try:
                self.github = Github(self.token)
                logger.info("GitHub統合を初期化しました")
            except Exception as e:
                logger.warning(f"GitHub統合の初期化エラー: {e}")
        else:
            if not GITHUB_PY_AVAILABLE:
                logger.warning("PyGithubがインストールされていません")
            if not self.token:
                logger.warning("GitHubトークンが設定されていません")
    
    def is_available(self) -> bool:
        """
        GitHub統合が利用可能かチェック
        
        Returns:
            利用可能な場合True
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
                "updated_at": repo_obj.updated_at.isoformat() if repo_obj.updated_at else None,
                "default_branch": repo_obj.default_branch,
                "open_issues": repo_obj.open_issues_count
            }
        except Exception as e:
            logger.error(f"リポジトリ情報取得エラー: {e}")
            return None
    
    def get_recent_commits(self, owner: str, repo: str, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """
        最近のコミットを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            branch: ブランチ名（デフォルト: main）
            limit: 取得件数
        
        Returns:
            コミット情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            commits = repo_obj.get_commits(sha=branch)[:limit]
            
            result = []
            for commit in commits:
                result.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name if commit.commit.author else None,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "url": commit.html_url
                })
            
            return result
        except Exception as e:
            logger.error(f"コミット取得エラー: {e}")
            return []
    
    def get_pull_requests(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        """
        プルリクエストを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            state: 状態（"open", "closed", "all"）
            limit: 取得件数
        
        Returns:
            プルリクエスト情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            prs = repo_obj.get_pulls(state=state)[:limit]
            
            result = []
            for pr in prs:
                result.append({
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "author": pr.user.login if pr.user else None,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                    "url": pr.html_url,
                    "mergeable": pr.mergeable
                })
            
            return result
        except Exception as e:
            logger.error(f"プルリクエスト取得エラー: {e}")
            return []
    
    def get_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        """
        イシューを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            state: 状態（"open", "closed", "all"）
            limit: 取得件数
        
        Returns:
            イシュー情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            issues = repo_obj.get_issues(state=state)[:limit]
            
            result = []
            for issue in issues:
                result.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "state": issue.state,
                    "author": issue.user.login if issue.user else None,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                    "url": issue.html_url,
                    "labels": [label.name for label in issue.labels]
                })
            
            return result
        except Exception as e:
            logger.error(f"イシュー取得エラー: {e}")
            return []
    
    def search_repositories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        リポジトリを検索
        
        Args:
            query: 検索クエリ
            limit: 取得件数
        
        Returns:
            リポジトリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            repos = self.github.search_repositories(query)[:limit]
            
            result = []
            for repo in repos:
                result.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                    "url": repo.html_url
                })
            
            return result
        except Exception as e:
            logger.error(f"リポジトリ検索エラー: {e}")
            return []
    
    def get_user_repositories(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ユーザーのリポジトリ一覧を取得
        
        Args:
            username: GitHubユーザー名
            limit: 取得件数
        
        Returns:
            リポジトリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            user = self.github.get_user(username)
            repos = user.get_repos()[:limit]
            
            result = []
            for repo in repos:
                result.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                    "url": repo.html_url,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
            
            return result
        except Exception as e:
            logger.error(f"ユーザーリポジトリ取得エラー: {e}")
            return []


def main():
    """テスト用メイン関数"""
    print("GitHub統合テスト")
    print("=" * 50)
    
    github = GitHubIntegration()
    
    if github.is_available():
        print("GitHub統合が利用可能です")
        
        # リポジトリ情報取得テスト
        repo_info = github.get_repository("comfyanonymous", "ComfyUI")
        if repo_info:
            print(f"\nリポジトリ情報:")
            print(f"  名前: {repo_info['name']}")
            print(f"  説明: {repo_info['description']}")
            print(f"  スター数: {repo_info['stars']}")
            print(f"  言語: {repo_info['language']}")
        
        # 最近のコミット取得テスト
        commits = github.get_recent_commits("comfyanonymous", "ComfyUI", limit=3)
        print(f"\n最近のコミット: {len(commits)}件")
        for commit in commits:
            print(f"  - {commit['message'][:50]}...")
    else:
        print("GitHub統合が利用できません")
        print("設定方法:")
        print("  1. pip install PyGithub")
        print("  2. 環境変数GITHUB_TOKENを設定")


if __name__ == "__main__":
    main()



