#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub高度な機能
リリース管理、統計、自動化など
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_integration import GitHubIntegration
from datetime import datetime
from typing import Dict, Any, List, Optional

class GitHubAdvancedFeatures:
    """GitHub高度な機能クラス"""
    
    def __init__(self):
        self.github = GitHubIntegration()
        if not self.github.is_available():
            raise Exception("GitHub統合が利用できません")
    
    def get_repo_statistics(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        リポジトリの統計情報を取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
        
        Returns:
            統計情報の辞書
        """
        repo_info = self.github.get_repository(owner, repo)
        if not repo_info:
            return {}
        
        commits = self.github.get_commits(owner, repo, limit=100)
        issues = self.github.get_issues(owner, repo, state="all", limit=100)
        prs = self.github.get_pull_requests(owner, repo, state="all", limit=100)
        
        return {
            "repository": {
                "name": repo_info["name"],
                "stars": repo_info["stars"],
                "forks": repo_info["forks"],
                "language": repo_info["language"],
                "url": repo_info["url"]
            },
            "commits": {
                "total_recent": len(commits),
                "latest": commits[0] if commits else None
            },
            "issues": {
                "total": len(issues),
                "open": len([i for i in issues if i["state"] == "open"]),
                "closed": len([i for i in issues if i["state"] == "closed"])
            },
            "pull_requests": {
                "total": len(prs),
                "open": len([p for p in prs if p["state"] == "open"]),
                "closed": len([p for p in prs if p["state"] == "closed"])
            }
        }
    
    def create_release_notes(self, owner: str, repo: str, tag: str, title: str) -> Optional[Dict[str, Any]]:
        """
        リリースノートを作成（GitHub CLIを使用）
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            tag: タグ名（例: v1.0.0）
            title: リリースタイトル
        
        Returns:
            リリース情報
        """
        import subprocess
        
        try:
            # 最新のコミットを取得してリリースノートを生成
            commits = self.github.get_commits(owner, repo, limit=20)
            
            notes = f"# {title}\n\n"
            notes += f"リリース日: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            notes += "## 変更内容\n\n"
            
            for commit in commits[:10]:
                message = commit["message"].split("\n")[0]
                notes += f"- {message}\n"
            
            # GitHub CLIでリリースを作成
            cmd = [
                "gh", "release", "create", tag,
                "--title", title,
                "--notes", notes,
                "--repo", f"{owner}/{repo}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            return {
                "tag": tag,
                "title": title,
                "url": f"https://github.com/{owner}/{repo}/releases/tag/{tag}",
                "created": True
            }
        except Exception as e:
            print(f"リリース作成エラー: {e}")
            return None
    
    def get_contribution_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        コントリビューション統計を取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
        
        Returns:
            統計情報
        """
        commits = self.github.get_commits(owner, repo, limit=100)
        
        # 作成者別のコミット数
        authors = {}
        for commit in commits:
            author = commit.get("author", "Unknown")
            authors[author] = authors.get(author, 0) + 1
        
        return {
            "total_commits": len(commits),
            "authors": authors,
            "period": {
                "first": commits[-1]["date"] if commits else None,
                "last": commits[0]["date"] if commits else None
            }
        }
    
    def auto_label_issues(self, owner: str, repo: str, keyword_labels: Dict[str, str]) -> int:
        """
        キーワードに基づいてイシューに自動ラベル付け
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            keyword_labels: キーワードとラベルのマッピング
        
        Returns:
            ラベル付けしたイシュー数
        """
        issues = self.github.get_issues(owner, repo, state="open", limit=100)
        labeled_count = 0
        
        for issue in issues:
            title = issue["title"].lower()
            body = (issue.get("body") or "").lower()
            text = f"{title} {body}"
            
            suggested_labels = []
            for keyword, label in keyword_labels.items():
                if keyword.lower() in text:
                    suggested_labels.append(label)
            
            if suggested_labels:
                # ラベルを追加（GitHub CLIを使用）
                import subprocess
                for label in suggested_labels:
                    try:
                        subprocess.run(
                            ["gh", "issue", "edit", str(issue["number"]),
                             "--add-label", label,
                             "--repo", f"{owner}/{repo}"],
                            capture_output=True,
                            check=False
                        )
                    except:
                        pass
                labeled_count += 1
        
        return labeled_count
    
    def generate_project_report(self, owner: str, repo: str) -> str:
        """
        プロジェクトレポートを生成
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
        
        Returns:
            レポート文字列
        """
        stats = self.get_repo_statistics(owner, repo)
        contrib = self.get_contribution_stats(owner, repo)
        
        report = f"""
# {stats['repository']['name']} プロジェクトレポート

生成日: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 リポジトリ情報

- **スター数**: {stats['repository']['stars']}
- **フォーク数**: {stats['repository']['forks']}
- **言語**: {stats['repository']['language']}
- **URL**: {stats['repository']['url']}

## 📝 コミット統計

- **最近のコミット数**: {stats['commits']['total_recent']}
- **最新コミット**: {stats['commits']['latest']['message'].split(chr(10))[0] if stats['commits']['latest'] else 'なし'}

## 🐛 イシュー統計

- **総数**: {stats['issues']['total']}
- **オープン**: {stats['issues']['open']}
- **クローズ**: {stats['issues']['closed']}

## 🔄 プルリクエスト統計

- **総数**: {stats['pull_requests']['total']}
- **オープン**: {stats['pull_requests']['open']}
- **クローズ**: {stats['pull_requests']['closed']}

## 👥 コントリビューション

- **総コミット数**: {contrib['total_commits']}
- **期間**: {contrib['period']['first']} ～ {contrib['period']['last']}

### 作成者別コミット数

"""
        for author, count in contrib['authors'].items():
            report += f"- {author}: {count}コミット\n"
        
        return report

def main():
    """メイン関数"""
    print("=" * 60)
    print("GitHub高度な機能")
    print("=" * 60)
    
    try:
        features = GitHubAdvancedFeatures()
        
        owner = "MRL-mana"
        repo = "manaos-integrations"
        
        print(f"\nリポジトリ: {owner}/{repo}")
        
        # 統計情報を取得
        print("\n統計情報を取得中...")
        stats = features.get_repo_statistics(owner, repo)
        
        print(f"\n📊 リポジトリ統計:")
        print(f"  スター数: {stats['repository']['stars']}")
        print(f"  フォーク数: {stats['repository']['forks']}")
        print(f"  言語: {stats['repository']['language']}")
        print(f"  最近のコミット: {stats['commits']['total_recent']}件")
        print(f"  イシュー: {stats['issues']['open']}オープン / {stats['issues']['closed']}クローズ")
        print(f"  PR: {stats['pull_requests']['open']}オープン / {stats['pull_requests']['closed']}クローズ")
        
        # プロジェクトレポートを生成
        print("\nプロジェクトレポートを生成中...")
        report = features.generate_project_report(owner, repo)
        
        # レポートをファイルに保存
        report_path = Path("github_project_report.md")
        report_path.write_text(report, encoding="utf-8")
        print(f"✅ レポートを保存しました: {report_path}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()






















