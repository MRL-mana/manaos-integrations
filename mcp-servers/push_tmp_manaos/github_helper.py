#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHubヘルパー機能
自動コミット・プッシュ、Issues/PR管理などの便利機能
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


class GitHubHelper:
    """GitHubヘルパークラス"""
    
    def __init__(self, token: Optional[str] = None, repo_path: Optional[str] = None):
        """
        初期化
        
        Args:
            token: GitHub Personal Access Token
            repo_path: リポジトリパス（Noneの場合は現在のディレクトリ）
        """
        self.github = None
        if GITHUB_INTEGRATION_AVAILABLE:
            self.github = GitHubIntegration(token)
            if not self.github.is_available():
                self.github = None
        
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
    
    def auto_commit(
        self,
        message: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> bool:
        """
        変更を自動コミット
        
        Args:
            message: コミットメッセージ（Noneの場合は自動生成）
            include_patterns: 含めるファイルパターン
            exclude_patterns: 除外するファイルパターン
        
        Returns:
            成功かどうか
        """
        if not (self.repo_path / ".git").exists():
            print("❌ Gitリポジトリが初期化されていません")
            return False
        
        try:
            # 変更があるかチェック
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                print("✅ コミットする変更がありません")
                return True
            
            # ファイルを追加
            if include_patterns:
                for pattern in include_patterns:
                    subprocess.run(
                        ["git", "add", pattern],
                        cwd=self.repo_path,
                        check=False
                    )
            elif exclude_patterns:
                # 除外パターンがある場合は個別に追加
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        file_path = line.split()[-1]
                        if not any(file_path.startswith(pattern) for pattern in exclude_patterns):
                            subprocess.run(
                                ["git", "add", file_path],
                                cwd=self.repo_path,
                                check=False
                            )
            else:
                subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            
            # コミットメッセージを生成
            if not message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Auto-commit: {timestamp}"
            
            # コミット
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True
            )
            print(f"✅ コミット完了: {message}")
            
            return True
            
        except Exception as e:
            print(f"❌ 自動コミットエラー: {e}")
            return False
    
    def auto_push(self, branch: Optional[str] = None, force: bool = False) -> bool:
        """
        変更を自動プッシュ
        
        Args:
            branch: ブランチ名（Noneの場合は現在のブランチ）
            force: 強制プッシュするかどうか
        
        Returns:
            成功かどうか
        """
        if not (self.repo_path / ".git").exists():
            print("❌ Gitリポジトリが初期化されていません")
            return False
        
        try:
            # ブランチを取得
            if not branch:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                branch = result.stdout.strip() or "main"
            
            # リモートがあるかチェック
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                print("⚠️ リモートリポジトリが設定されていません")
                return False
            
            # プッシュ
            push_cmd = ["git", "push"]
            if force:
                push_cmd.append("--force")
            push_cmd.extend(["-u", "origin", branch])
            
            subprocess.run(push_cmd, cwd=self.repo_path, check=True)
            print(f"✅ プッシュ完了: {branch}")
            
            return True
            
        except Exception as e:
            print(f"❌ 自動プッシュエラー: {e}")
            return False
    
    def create_issue_from_error(
        self,
        owner: str,
        repo: str,
        error_message: str,
        error_type: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        エラーからイシューを作成
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            error_message: エラーメッセージ
            error_type: エラータイプ
            labels: ラベルリスト
        
        Returns:
            作成されたイシュー情報
        """
        if not self.github or not self.github.is_available():
            print("❌ GitHub統合が利用できません")
            return None
        
        title = f"[{error_type or 'Error'}] {error_message[:50]}"
        body = f"""## エラー情報

**タイプ**: {error_type or 'Unknown'}
**発生時刻**: {datetime.now().isoformat()}

### エラーメッセージ
```
{error_message}
```

### 環境情報
- Python: {os.sys.version}
- OS: {os.name}
"""
        
        return self.github.create_issue(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            labels=labels or ["bug", "error"]
        )
    
    def sync_with_github(
        self,
        owner: str,
        repo: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        GitHubと同期（プル→コミット→プッシュ）
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            branch: ブランチ名
        
        Returns:
            同期結果
        """
        result = {
            "pull": False,
            "commit": False,
            "push": False,
            "errors": []
        }
        
        try:
            # プル
            subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=self.repo_path,
                check=True
            )
            result["pull"] = True
            print("✅ プル完了")
            
            # コミット
            if self.auto_commit():
                result["commit"] = True
            
            # プッシュ
            if self.auto_push(branch):
                result["push"] = True
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"❌ 同期エラー: {e}")
        
        return result


def main():
    """メイン関数"""
    print("GitHubヘルパー")
    print("=" * 60)
    
    helper = GitHubHelper()
    
    # 状態を確認
    if (helper.repo_path / ".git").exists():
        print("✅ Gitリポジトリ: 初期化済み")
    else:
        print("⚠️ Gitリポジトリ: 未初期化")
    
    if helper.github and helper.github.is_available():
        print("✅ GitHub統合: 利用可能")
    else:
        print("⚠️ GitHub統合: 利用不可")


if __name__ == "__main__":
    main()






















