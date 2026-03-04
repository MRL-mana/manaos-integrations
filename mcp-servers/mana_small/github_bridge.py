#!/usr/bin/env python3
"""
GitHub API Bridge for ManaOS
- GitHub API操作のラッパー
- .mana_vaultからトークンを安全に読み込み
- ファイルの作成・更新・削除をサポート
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any
import requests

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vaultディレクトリ
VAULT_DIR = Path("/root/.mana_vault")
# 既存のトークンファイル名の候補（優先順位順）
GITHUB_TOKEN_FILES = [
    VAULT_DIR / "github_token.txt",  # 新規
    VAULT_DIR / "github_token",      # 既存
    VAULT_DIR / "github_pat",        # 既存
    VAULT_DIR / "github_workflow_token.txt",  # 既存
]
GITHUB_CONFIG_FILE = VAULT_DIR / "github_config.json"


class GitHubBridge:
    """GitHub API操作のブリッジクラス"""

    def __init__(self, token: Optional[str] = None, owner: Optional[str] = None, repo: Optional[str] = None):
        """
        GitHub Bridge初期化

        Args:
            token: GitHub Personal Access Token（未指定時は.mana_vaultから読み込み）
            owner: リポジトリオーナー（未指定時はconfigから読み込み）
            repo: リポジトリ名（未指定時はconfigから読み込み）
        """
        self.token = token or self._load_token()
        self.owner = owner or self._load_config().get("owner", "MRL-mana")
        self.repo = repo or self._load_config().get("repo", "manaos-knowledge")

        if not self.token:
            raise ValueError(
                f"GitHub token is required. Set it in one of: {[f.name for f in GITHUB_TOKEN_FILES]}")

        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ManaOS-GitHub-Bridge"
        }

    def _load_token(self) -> Optional[str]:
        """.mana_vaultからGitHubトークンを読み込み（複数のファイル名に対応）"""
        try:
            # 既存のトークンファイルを順番に試す
            for token_file in GITHUB_TOKEN_FILES:
                if token_file.exists():
                    token = token_file.read_text().strip()
                    if token:  # 空でないことを確認
                        logger.info(
                            f"✅ GitHub token loaded from: {token_file.name}")
                        return token

            # 見つからなかった場合
            logger.warning(
                f"⚠️ GitHub token file not found. Tried: {[f.name for f in GITHUB_TOKEN_FILES]}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load GitHub token: {e}")
            return None

    def _load_config(self) -> Dict[str, str]:
        """GitHub設定を読み込み"""
        try:
            if GITHUB_CONFIG_FILE.exists():
                config = json.loads(GITHUB_CONFIG_FILE.read_text())
                logger.info("✅ GitHub config loaded")
                return config
            else:
                # デフォルト設定
                default_config = {
                    "owner": "MRL-mana",
                    "repo": "manaos-knowledge"
                }
                logger.info("ℹ️ Using default GitHub config")
                return default_config
        except Exception as e:
            logger.error(f"❌ Failed to load GitHub config: {e}")
            return {"owner": "MRL-mana", "repo": "manaos-knowledge"}

    def _get_file_sha(self, path: str) -> Optional[str]:
        """既存ファイルのSHAを取得"""
        try:
            url = f"{self.base_url}/contents/{path}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("sha")
            elif response.status_code == 404:
                # ファイルが存在しない
                return None
            else:
                logger.warning(
                    f"⚠️ Failed to get file SHA: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting file SHA: {e}")
            return None

    def push_file(
        self,
        path: str,
        content: str,
        message: str = "Update via ManaOS GitHub Bridge",
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        ファイルをGitHubにプッシュ（作成・更新）

        Args:
            path: リポジトリ内のファイルパス
            content: ファイル内容
            message: コミットメッセージ
            branch: ブランチ名（デフォルト: main）

        Returns:
            レスポンス辞書
        """
        try:
            url = f"{self.base_url}/contents/{path}"

            # 既存ファイルのSHAを取得
            sha = self._get_file_sha(path)

            # Base64エンコード
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')

            # リクエストデータ
            data = {
                "message": message,
                "content": content_base64,
                "branch": branch
            }

            # SHAがある場合は更新、ない場合は新規作成
            if sha:
                data["sha"] = sha
                logger.info(f"📝 Updating file: {path}")
            else:
                logger.info(f"✨ Creating new file: {path}")

            # APIリクエスト
            response = requests.put(
                url, json=data, headers=self.headers, timeout=30)

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✅ Successfully pushed file: {path}")
                return {
                    "success": True,
                    "path": path,
                    "sha": result.get("content", {}).get("sha"),
                    "message": "File pushed successfully"
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(f"❌ Failed to push file: {error_msg}")
                return {
                    "success": False,
                    "path": path,
                    "error": error_msg,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Error pushing file: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def get_file(self, path: str, branch: str = "main") -> Dict[str, Any]:
        """
        ファイルをGitHubから取得

        Args:
            path: リポジトリ内のファイルパス
            branch: ブランチ名（デフォルト: main）

        Returns:
            ファイル内容とメタデータ
        """
        try:
            url = f"{self.base_url}/contents/{path}"
            params = {"ref": branch} if branch else {}

            response = requests.get(
                url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Base64デコード
                content = base64.b64decode(data["content"]).decode('utf-8')
                return {
                    "success": True,
                    "content": content,
                    "sha": data.get("sha"),
                    "size": data.get("size"),
                    "path": data.get("path")
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "File not found"
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Error getting file: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def delete_file(
        self,
        path: str,
        message: str = "Delete via ManaOS GitHub Bridge",
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        ファイルをGitHubから削除

        Args:
            path: リポジトリ内のファイルパス
            message: コミットメッセージ
            branch: ブランチ名（デフォルト: main）

        Returns:
            レスポンス辞書
        """
        try:
            url = f"{self.base_url}/contents/{path}"

            # 既存ファイルのSHAを取得
            sha = self._get_file_sha(path)
            if not sha:
                return {
                    "success": False,
                    "error": "File not found"
                }

            # リクエストデータ
            data = {
                "message": message,
                "sha": sha,
                "branch": branch
            }

            # APIリクエスト
            response = requests.delete(
                url, json=data, headers=self.headers, timeout=30)

            if response.status_code == 200:
                logger.info(f"✅ Successfully deleted file: {path}")
                return {
                    "success": True,
                    "path": path,
                    "message": "File deleted successfully"
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(f"❌ Failed to delete file: {error_msg}")
                return {
                    "success": False,
                    "path": path,
                    "error": error_msg,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def list_files(self, path: str = "", branch: str = "main") -> Dict[str, Any]:
        """
        ディレクトリ内のファイル一覧を取得

        Args:
            path: リポジトリ内のディレクトリパス（空文字列でルート）
            branch: ブランチ名（デフォルト: main）

        Returns:
            ファイル一覧
        """
        try:
            url = f"{self.base_url}/contents/{path}" if path else f"{self.base_url}/contents"
            params = {"ref": branch} if branch else {}

            response = requests.get(
                url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                items = response.json()
                files = [
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "type": item["type"],
                        "size": item.get("size", 0)
                    }
                    for item in items
                ]
                return {
                    "success": True,
                    "files": files,
                    "count": len(files)
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"❌ Error listing files: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """GitHub接続テスト"""
        try:
            url = f"{self.base_url}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                repo_info = response.json()
                return {
                    "success": True,
                    "repo": repo_info.get("full_name"),
                    "description": repo_info.get("description"),
                    "private": repo_info.get("private"),
                    "message": "Connection successful"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": response.json().get("message", "Unknown error")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 便利関数
def push_file(path: str, content: str, message: str = "Update via ManaOS") -> Dict[str, Any]:
    """簡単なファイルプッシュ関数"""
    bridge = GitHubBridge()
    return bridge.push_file(path, content, message)


def get_file(path: str) -> Dict[str, Any]:
    """簡単なファイル取得関数"""
    bridge = GitHubBridge()
    return bridge.get_file(path)


if __name__ == "__main__":
    # テスト実行
    print("🧪 Testing GitHub Bridge...")

    bridge = GitHubBridge()

    # 接続テスト
    print("\n1. Connection test:")
    result = bridge.test_connection()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # ファイル一覧取得テスト
    print("\n2. List files test:")
    result = bridge.list_files()
    if result.get("success"):
        print(f"Found {result.get('count')} items")
        for file in result.get("files", [])[:5]:  # 最初の5つだけ表示
            print(f"  - {file['name']} ({file['type']})")
    else:
        print(f"Error: {result.get('error')}")
