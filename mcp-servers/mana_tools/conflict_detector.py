#!/usr/bin/env python3
"""
ManaOS 競合検知システム
同一ファイルへの重複提案を検出し、適切な対処を実行
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

CONFLICT_WINDOW_HOURS = 24
PR_MEMORY_FILE = Path("/root/github_pr_memory.json")

class ConflictDetector:
    """競合検知クラス"""

    def __init__(self, memory_file: Path = PR_MEMORY_FILE):
        self.memory_file = memory_file
        self.pr_history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """PR履歴を読み込む"""
        if not self.memory_file.exists():
            return []

        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f).get("prs", [])
        except IOError:
            return []

    def _save_history(self):
        """PR履歴を保存"""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_updated": datetime.now().isoformat(),
            "prs": self.pr_history
        }
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def detect_conflicts(self, pr_number: int, pr_files: List[str], pr_author: str, pr_created_at: str) -> Tuple[bool, List[Dict]]:
        """競合を検出"""
        conflicts = []
        cutoff_time = datetime.now() - timedelta(hours=CONFLICT_WINDOW_HOURS)

        for existing_pr in self.pr_history:
            # 自分自身はスキップ
            if existing_pr.get("number") == pr_number:
                continue

            # 時間範囲チェック
            try:
                pr_time = datetime.fromisoformat(existing_pr.get("created_at", ""))
                if pr_time < cutoff_time:
                    continue  # 古すぎるPRはスキップ
            except Exception:
                continue

            # ファイル重複チェック
            existing_files = existing_pr.get("files", [])
            overlapping_files = set(pr_files) & set(existing_files)

            if overlapping_files:
                conflicts.append({
                    "pr_number": existing_pr.get("number"),
                    "pr_author": existing_pr.get("author"),
                    "pr_title": existing_pr.get("title", ""),
                    "pr_created_at": existing_pr.get("created_at"),
                    "overlapping_files": list(overlapping_files),
                    "conflict_type": self._determine_conflict_type(
                        pr_files, existing_files, overlapping_files  # type: ignore
                    )
                })

        # 現在のPRを履歴に追加
        self._add_to_history(pr_number, pr_files, pr_author, pr_created_at)

        return len(conflicts) > 0, conflicts

    def _determine_conflict_type(self, current_files: List[str], existing_files: List[str], overlapping: List[str]) -> str:
        """競合タイプを判定"""
        # 完全一致
        if set(current_files) == set(existing_files):
            return "full_overlap"

        # 現在のPRが範囲広すぎ
        if len(current_files) > len(existing_files) * 2:
            return "current_too_wide"

        # 既存のPRが範囲広すぎ
        if len(existing_files) > len(current_files) * 2:
            return "existing_too_wide"

        # 部分的重複
        return "partial_overlap"

    def _add_to_history(self, pr_number: int, files: List[str], author: str, created_at: str):
        """PRを履歴に追加"""
        pr_entry = {
            "number": pr_number,
            "files": files,
            "author": author,
            "created_at": created_at,
            "detected_at": datetime.now().isoformat()
        }

        # 既存の同じPRを置き換え
        self.pr_history = [p for p in self.pr_history if p.get("number") != pr_number]
        self.pr_history.append(pr_entry)

        # 古いエントリを削除（過去7日以外）
        cutoff = datetime.now() - timedelta(days=7)
        filtered_history = []
        for p in self.pr_history:
            created_at = p.get("created_at", "")
            if created_at:
                try:
                    if datetime.fromisoformat(created_at) > cutoff:
                        filtered_history.append(p)
                except (ValueError, TypeError):
                    # 無効な日付形式はスキップ
                    pass
        self.pr_history = filtered_history

        self._save_history()

    def suggest_resolution(self, conflict: Dict) -> str:
        """解決策を提案"""
        conflict_type = conflict.get("conflict_type", "")

        if conflict_type == "full_overlap":
            return (
                f"⚠️  PR #{conflict['pr_number']} と完全に重複しています。\n"
                f"既存のPRを確認し、必要に応じてクローズまたはマージしてください。"
            )

        elif conflict_type == "current_too_wide":
            return (
                f"⚠️  PR #{conflict['pr_number']} が同じファイルを変更しています。\n"
                f"現在のPRが範囲広すぎるため、分割を検討してください。\n"
                f"重複ファイル: {', '.join(conflict['overlapping_files'][:3])}"
            )

        elif conflict_type == "existing_too_wide":
            return (
                f"⚠️  PR #{conflict['pr_number']} が同じファイルを変更しています。\n"
                f"既存のPRが範囲広すぎるため、分割を依頼するか、待機してください。"
            )

        else:  # partial_overlap
            return (
                f"⚠️  PR #{conflict['pr_number']} と一部のファイルが重複しています。\n"
                f"重複ファイル: {', '.join(conflict['overlapping_files'])}\n"
                f"協調して変更を進めるか、重複部分を分離してください。"
            )

    def get_recent_prs_for_file(self, file_path: str, hours: int = 24) -> List[Dict]:
        """特定ファイルの最近のPRを取得"""
        cutoff = datetime.now() - timedelta(hours=hours)
        matching_prs = []

        for pr in self.pr_history:
            if file_path in pr.get("files", []):
                try:
                    pr_time = datetime.fromisoformat(pr.get("created_at", ""))
                    if pr_time > cutoff:
                        matching_prs.append(pr)
                except IOError:
                    pass

        return matching_prs

def main():
    """テスト用"""
    detector = ConflictDetector()

    # テストPR
    pr_files = ["adapters/model_v1.py", "config/learning.yaml"]
    has_conflicts, conflicts = detector.detect_conflicts(
        pr_number=123,
        pr_files=pr_files,
        pr_author="trinity",
        pr_created_at=datetime.now().isoformat()
    )

    if has_conflicts:
        print("❌ Conflicts detected:")
        for conflict in conflicts:
            print(f"  - PR #{conflict['pr_number']}: {conflict['conflict_type']}")
            print(f"    {detector.suggest_resolution(conflict)}")
    else:
        print("✅ No conflicts detected")

if __name__ == "__main__":
    main()

