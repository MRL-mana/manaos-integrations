#!/usr/bin/env python3
"""
ManaOS ポリシーシステム クイックスタート
エージェントが簡単に使える統合ラッパー
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.policy.action_queue import ActionQueue
from tools.policy.conflict_detector import ConflictDetector
from tools.policy.check import PolicyChecker

class ManaOSPolicy:
    """ポリシーシステムの統合ラッパー"""

    def __init__(self):
        self.queue = ActionQueue()
        self.detector = ConflictDetector()
        self.checker = PolicyChecker()

    def propose_action(self, agent: str, resource: str, intent: str, files: List[str], data: Dict = None) -> Dict:  # type: ignore
        """
        アクションを提案（エージェント用）

        Args:
            agent: エージェント名（trinity/remi/machi/luna）
            resource: リソース名（例: adapters/model_v1）
            intent: 意図（例: update_learning_adapter）
            files: 変更対象ファイルのリスト
            data: 追加データ

        Returns:
            提案結果（action_id, conflicts, policy_check_result）
        """
        # 1. PAUSE_AUTOフラグチェック
        if self.checker.check_pause_flag():
            return {
                "success": False,
                "error": "PAUSE_AUTO flag is active. All automatic actions are paused."
            }

        # 2. 競合検知
        has_conflicts, conflicts = self.detector.detect_conflicts(
            pr_number=0,  # 実際のPR番号は後で設定
            pr_files=files,
            pr_author=agent,
            pr_created_at=datetime.now().isoformat()
        )

        # 3. アクションをキューに追加
        action = {
            "agent": agent,
            "resource": resource,
            "intent": intent,
            "files": files,
            "data": data or {}
        }
        action_id = self.queue.enqueue(action)

        # 4. リソースロックを試行
        lock_acquired = self.queue.acquire_lock(resource, action_id)

        return {
            "success": True,
            "action_id": action_id,
            "lock_acquired": lock_acquired,
            "conflicts": conflicts if has_conflicts else [],
            "message": "Action queued successfully" if lock_acquired else "Action queued, waiting for lock"
        }

    def check_policy_for_pr(self, pr_number: int, pr_author: str, pr_title: str, pr_files: List[str]) -> Dict:
        """
        PRのポリシーチェック

        Returns:
            チェック結果（passed, violations, warnings）
        """
        # 環境変数を設定（check.pyが使用）
        import os
        os.environ["PR_NUMBER"] = str(pr_number)
        os.environ["PR_AUTHOR"] = pr_author
        os.environ["PR_TITLE"] = pr_title
        os.environ["PR_BASE"] = "main"

        # ポリシーチェック実行
        passed, errors = self.checker.check_all(pr_number)

        return {
            "passed": passed,
            "violations": self.checker.violations,
            "warnings": self.checker.warnings,
            "info_messages": self.checker.info_messages
        }

def main():
    """使用例"""
    policy = ManaOSPolicy()

    # 例: Trinityが学習アダプタを更新したい場合
    result = policy.propose_action(
        agent="trinity",
        resource="adapters/model_v1",
        intent="update_learning_adapter",
        files=["adapters/model_v1.py", "config/learning.yaml"],
        data={"learning_rate": 0.001}
    )

    print(f"提案結果: {result}")

    if result["success"]:
        if result["conflicts"]:
            print(f"⚠️  競合が検出されました: {len(result['conflicts'])}件")
        else:
            print("✅ 競合なし、キューに追加されました")

    # PRポリシーチェックの例
    pr_check = policy.check_policy_for_pr(
        pr_number=123,
        pr_author="trinity",
        pr_title="trinity/adapters/update_learning_adapter",
        pr_files=["adapters/model_v1.py"]
    )

    print(f"\nPRチェック結果: passed={pr_check['passed']}")

if __name__ == "__main__":
    from typing import List, Dict
    main()

