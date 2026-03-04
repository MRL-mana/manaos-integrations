#!/usr/bin/env python3
"""
ManaOS ポリシーチェックスクリプト
PRのポリシー違反を検出し、適切なアクションを実行
"""

import sys
import os
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pytz

# 設定ファイルパス
POLICIES_FILE = Path("/root/infra/policies/manaos-policies.yaml")
PAUSE_AUTO_FLAG = Path("/root/infra/flags/PAUSE_AUTO")
QUEUE_DIR = Path("/root/actions/queue")
LOCKS_DIR = Path("/root/actions/locks")
OBSERVABILITY_LOG = Path("/root/logs/policy_observability.log")

class PolicyChecker:
    def __init__(self, policies_file: Path = POLICIES_FILE):
        self.policies_file = policies_file
        self.policies = self._load_policies()
        self.violations = []
        self.warnings = []
        self.info_messages = []

    def _load_policies(self) -> Dict:
        """ポリシーファイルを読み込む"""
        if not self.policies_file.exists():
            print(f"⚠️  Policies file not found: {self.policies_file}")
            return {}

        with open(self.policies_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def check_pause_flag(self) -> bool:
        """PAUSE_AUTOフラグをチェック"""
        if PAUSE_AUTO_FLAG.exists():
            print(f"❌ PAUSE_AUTO flag is active at {PAUSE_AUTO_FLAG}")
            print("   All automatic actions are paused. Manual intervention required.")
            return True
        return False

    def load_pr_data(self, pr_number: Optional[int] = None) -> Dict:
        """PRデータを読み込む（GitHub CLIまたは環境変数から）"""
        # 実際の実装ではGitHub APIを使用
        # ここでは簡易的な実装
        pr_data = {
            "number": pr_number or int(os.environ.get("PR_NUMBER", "0")),
            "author": os.environ.get("PR_AUTHOR", "unknown"),
            "title": os.environ.get("PR_TITLE", ""),
            "files": self._get_pr_files(),
            "labels": [],
            "base": os.environ.get("PR_BASE", "main"),
            "created_at": datetime.now().isoformat(),
        }
        return pr_data

    def _get_pr_files(self) -> List[str]:
        """PRで変更されたファイルリストを取得"""
        # 実際の実装ではgit diffを使用
        import subprocess
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.SubprocessError:
            return []

    def check_protect_decisions(self, pr_data: Dict) -> bool:
        """決定保護ポリシーをチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "protect-decisions"), None)
        if not policy:
            return True

        matched_files = []
        for file_path in pr_data.get("files", []):
            for pattern in policy.get("match", []):
                if self._match_pattern(file_path, pattern):
                    matched_files.append(file_path)

        if matched_files:
            agent = pr_data.get("author", "").lower()
            if agent in policy.get("deny_agents", []):
                self.violations.append({
                    "policy": "protect-decisions",
                    "message": policy.get("message", ""),
                    "files": matched_files,
                    "agent": agent
                })
                return False
        return True

    def check_rate_limit(self, pr_data: Dict) -> bool:
        """レート制限をチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "rate-limit-train"), None)
        if not policy:
            return True

        matched_files = []
        for file_path in pr_data.get("files", []):
            for pattern in policy.get("match", []):
                if self._match_pattern(file_path, pattern):
                    matched_files.append(file_path)

        if matched_files:
            # 過去1週間の変更数をカウント
            count = self._count_recent_changes(matched_files, days=7)
            if count >= policy.get("max_per_week", 2):
                self.warnings.append({
                    "policy": "rate-limit-train",
                    "message": policy.get("message", ""),
                    "count": count,
                    "limit": policy.get("max_per_week", 2)
                })
                return False
        return True

    def check_night_changes(self, pr_data: Dict) -> bool:
        """夜間変更ブロックをチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "no-night-changes"), None)
        if not policy:
            return True

        window_block = policy.get("window_block", "22:00-07:00 JST")
        timezone_str = policy.get("timezone", "Asia/Tokyo")

        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            hour = now.hour

            # 22:00-07:00の範囲をチェック
            if hour >= 22 or hour < 7:
                self.violations.append({
                    "policy": "no-night-changes",
                    "message": policy.get("message", ""),
                    "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")
                })
                return False
        except Exception as e:
            print(f"⚠️  Timezone check failed: {e}")

        return True

    def check_pr_title_format(self, pr_data: Dict) -> bool:
        """PRタイトルフォーマットをチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "enforce-pr-title-format"), None)
        if not policy:
            return True

        title = pr_data.get("title", "")
        required_format = policy.get("required_format", "{agent}/{resource}/{intent}")

        # 簡易チェック：{agent}/{resource}/{intent} の形式か
        pattern = r'^[^/]+/[^/]+/[^/]+'
        if not re.match(pattern, title):
            self.warnings.append({
                "policy": "enforce-pr-title-format",
                "message": policy.get("message", ""),
                "current_title": title,
                "required_format": required_format
            })
            return False
        return True

    def check_conflicts(self, pr_data: Dict) -> bool:
        """同一ファイルへの競合をチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "detect-conflicts"), None)
        if not policy:
            return True

        conflict_window = policy.get("conflict_window_hours", 24)
        pr_files = pr_data.get("files", [])

        # 実際の実装では、最近のPRをチェックして競合を検出
        # ここでは簡易実装
        conflicts = self._detect_file_conflicts(pr_files, hours=conflict_window)

        if conflicts:
            self.info_messages.append({
                "policy": "detect-conflicts",
                "message": policy.get("message", ""),
                "conflicts": conflicts
            })
        return True

    def check_large_changes(self, pr_data: Dict) -> bool:
        """大規模変更の分割要求をチェック"""
        policy = next((p for p in self.policies.get("policies", []) if p.get("name") == "require-split-large-changes"), None)
        if not policy:
            return True

        files = pr_data.get("files", [])
        max_files = policy.get("max_files_per_pr", 20)
        max_lines = policy.get("max_lines_per_pr", 500)

        if len(files) > max_files:
            self.warnings.append({
                "policy": "require-split-large-changes",
                "message": policy.get("message", ""),
                "file_count": len(files),
                "max_files": max_files
            })
            return False

        # 行数チェック（実際の実装ではgit diff --statを使用）
        # 簡易実装のためスキップ
        return True

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """ファイルパスがパターンにマッチするかチェック"""
        # ** を正規表現に変換
        regex_pattern = pattern.replace("**", ".*").replace("*", "[^/]*")
        return bool(re.match(regex_pattern, file_path))

    def _count_recent_changes(self, file_patterns: List[str], days: int) -> int:
        """最近の変更数をカウント"""
        # 実際の実装ではgit logを使用
        # 簡易実装のため0を返す
        return 0

    def _detect_file_conflicts(self, files: List[str], hours: int) -> List[Dict]:
        """ファイル競合を検出"""
        # 実際の実装ではGitHub APIを使用して最近のPRをチェック
        # 簡易実装のため空リストを返す
        return []

    def check_all(self, pr_number: Optional[int] = None) -> Tuple[bool, List[str]]:
        """すべてのポリシーチェックを実行"""
        # PAUSE_AUTOフラグチェック
        if self.check_pause_flag():
            return False, ["PAUSE_AUTO flag is active"]

        # PRデータを読み込む
        pr_data = self.load_pr_data(pr_number)

        # 各ポリシーをチェック
        checks = [
            self.check_protect_decisions,
            self.check_rate_limit,
            self.check_night_changes,
            self.check_pr_title_format,
            self.check_conflicts,
            self.check_large_changes,
        ]

        for check in checks:
            try:
                check(pr_data)
            except Exception as e:
                print(f"⚠️  Check failed: {check.__name__}: {e}")

        # 結果を表示
        all_passed = len(self.violations) == 0

        if self.violations:
            print("\n❌ Policy Violations:")
            for violation in self.violations:
                print(f"  - {violation['policy']}: {violation['message']}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning['policy']}: {warning['message']}")

        if self.info_messages:
            print("\nℹ️  Info:")
            for info in self.info_messages:
                print(f"  - {info['policy']}: {info['message']}")

        # 観測ログに記録
        self._log_observability(pr_data)

        return all_passed, [v['message'] for v in self.violations]

    def _log_observability(self, pr_data: Dict):
        """観測ログに記録"""
        if not self.policies.get("observability"):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "pr_number": pr_data.get("number"),
            "pr_author": pr_data.get("author"),
            "violations": len(self.violations),
            "warnings": len(self.warnings),
            "info_messages": len(self.info_messages),
        }

        OBSERVABILITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(OBSERVABILITY_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

def main():
    """メイン処理"""

    pr_number = None
    if len(sys.argv) > 1:
        try:
            pr_number = int(sys.argv[-1])
        except ValueError:
            pass

    checker = PolicyChecker()
    passed, errors = checker.check_all(pr_number)

    if not passed:
        print("\n❌ Policy check failed")
        sys.exit(1)
    else:
        print("\n✅ Policy check passed")
        sys.exit(0)

if __name__ == "__main__":
    main()

