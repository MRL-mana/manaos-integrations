#!/usr/bin/env python3
"""
Trinityエージェント向けポリシーシステム統合
エージェントが簡単に使えるヘルパー関数
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.policy.quick_start import ManaOSPolicy
from datetime import datetime
from typing import Dict, List, Optional

class AgentPolicyHelper:
    """エージェント用ポリシーヘルパー"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name.lower()
        self.policy = ManaOSPolicy()

    def propose_change(self, resource: str, intent: str, files: List[str],
                      description: str = "", data: Optional[Dict] = None) -> Dict:
        """
        変更を提案（エージェント用の簡易インターフェース）

        Args:
            resource: リソース名（例: "adapters/model_v1"）
            intent: 意図（例: "update_learning_adapter"）
            files: 変更対象ファイルのリスト
            description: 説明（オプション）
            data: 追加データ（オプション）

        Returns:
            提案結果
        """
        # PAUSE_AUTOフラグチェック
        if self.policy.checker.check_pause_flag():
            return {
                "success": False,
                "error": "PAUSE_AUTO flag is active. All automatic actions are paused.",
                "action": "wait"
            }

        # アクションを提案
        result = self.policy.propose_action(
            agent=self.agent_name,
            resource=resource,
            intent=intent,
            files=files,
            data=data or {}
        )

        if not result["success"]:
            return result

        # 競合がある場合は警告
        if result.get("conflicts"):
            conflicts_info = []
            for conflict in result["conflicts"]:
                conflicts_info.append({
                    "pr_number": conflict.get("pr_number"),
                    "conflict_type": conflict.get("conflict_type"),
                    "overlapping_files": conflict.get("overlapping_files", [])
                })

            result["warning"] = f"競合が検出されました: {len(result['conflicts'])}件"
            result["conflicts_info"] = conflicts_info

        # アクションIDと説明を追加
        result["description"] = description
        result["proposed_at"] = datetime.now().isoformat()

        return result

    def check_before_pr(self, pr_title: str, pr_files: List[str],
                       pr_number: Optional[int] = None) -> Dict:
        """
        PR作成前のポリシーチェック

        Args:
            pr_title: PRタイトル（{agent}/{resource}/{intent}形式）
            pr_files: 変更ファイルのリスト
            pr_number: PR番号（オプション）

        Returns:
            チェック結果
        """
        check_result = self.policy.check_policy_for_pr(
            pr_number=pr_number or 0,
            pr_author=self.agent_name,
            pr_title=pr_title,
            pr_files=pr_files
        )

        return {
            "can_proceed": check_result["passed"],
            "violations": check_result["violations"],
            "warnings": check_result["warnings"],
            "recommendations": self._generate_recommendations(check_result)
        }

    def _generate_recommendations(self, check_result: Dict) -> List[str]:
        """推奨事項を生成"""
        recommendations = []

        if check_result["violations"]:
            recommendations.append("❌ ポリシー違反があります。修正が必要です。")

        if check_result["warnings"]:
            recommendations.append("⚠️  警告があります。確認してください。")

        # PRタイトルフォーマットチェック
        for warning in check_result.get("warnings", []):
            if warning.get("policy") == "enforce-pr-title-format":
                recommendations.append(
                    f"💡 PRタイトルを '{warning.get('required_format')}' 形式にしてください"
                )

        return recommendations

    def get_queue_status(self) -> Dict:
        """キュー状態を取得"""
        return self.policy.queue.get_queue_status()

    def is_paused(self) -> bool:
        """PAUSE_AUTOフラグの状態を確認"""
        return self.policy.checker.check_pause_flag()

# エージェント別の簡易インターフェース
def get_agent_policy(agent_name: str) -> AgentPolicyHelper:
    """エージェント名からポリシーヘルパーを取得"""
    return AgentPolicyHelper(agent_name)

# 使用例
if __name__ == "__main__":
    # Remiが使用する場合
    remi = get_agent_policy("remi")

    result = remi.propose_change(
        resource="adapters/model_v1",
        intent="update_learning_adapter",
        files=["adapters/model_v1.py"],
        description="学習率を0.001に更新"
    )

    print(f"Remiの提案結果: {result}")

    # PR前チェック
    check = remi.check_before_pr(
        pr_title="remi/adapters/update_learning_adapter",
        pr_files=["adapters/model_v1.py"]
    )
    print(f"\nPR前チェック: {check}")



