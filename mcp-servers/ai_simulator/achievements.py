"""
Achievements & Quests システム
実績・クエストの定義とチェックロジック
"""

from typing import Dict, Any, List, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 実績定義
ACHIEVEMENTS_DEF = [
    # 速度系
    {
        "id": "fast0",
        "name": "光速昇格",
        "desc": "A→Cを同日で達成",
        "tier": "gold",
        "category": "speed",
    },
    {
        "id": "fast1",
        "name": "瞬速実装",
        "desc": "1日でStageを1つ以上実装",
        "tier": "silver",
        "category": "speed",
    },
    # 安全系
    {
        "id": "safe1",
        "name": "セーフティ職人",
        "desc": "KillSwitch/ロールバック実装",
        "tier": "silver",
        "category": "safety",
    },
    {
        "id": "safe2",
        "name": "緊急停止マスター",
        "desc": "緊急停止を10回以上実行",
        "tier": "bronze",
        "category": "safety",
    },
    # 監視系
    {
        "id": "ops1",
        "name": "監視の鬼",
        "desc": "メトリクス10種以上",
        "tier": "bronze",
        "category": "monitoring",
    },
    {
        "id": "ops2",
        "name": "メトリクスマニア",
        "desc": "1日で100回以上のメトリクス収集",
        "tier": "silver",
        "category": "monitoring",
    },
    # 試行系
    {
        "id": "shadow50",
        "name": "Shadow試行50回",
        "desc": "夜間に安全試行を50回完了する",
        "tier": "bronze",
        "category": "trials",
    },
    {
        "id": "shadow100",
        "name": "Shadow試行100回",
        "desc": "Shadow Modeで100回試行",
        "tier": "silver",
        "category": "trials",
    },
    {
        "id": "canary10",
        "name": "Canaryデプロイ",
        "desc": "Canary Modeで10%デプロイ成功",
        "tier": "silver",
        "category": "trials",
    },
    # 信頼度系
    {
        "id": "trust90",
        "name": "信頼度90%維持",
        "desc": "confidence 0.90を3時間維持",
        "tier": "gold",
        "category": "trust",
    },
    {
        "id": "trust95",
        "name": "信頼度95%超",
        "desc": "confidence 0.95以上を達成",
        "tier": "legend",
        "category": "trust",
    },
    # パフォーマンス系
    {
        "id": "slo1",
        "name": "SLO遵守",
        "desc": "p95 ≤ 3000ms を維持",
        "tier": "bronze",
        "category": "performance",
    },
    {
        "id": "slo2",
        "name": "超高速SLO",
        "desc": "p95 ≤ 1000ms を達成",
        "tier": "gold",
        "category": "performance",
    },
    # 報酬系
    {
        "id": "reward5",
        "name": "ΔReward +5%",
        "desc": "ベースライン比+5%を達成",
        "tier": "silver",
        "category": "reward",
    },
    {
        "id": "reward10",
        "name": "ΔReward +10%",
        "desc": "ベースライン比+10%を達成",
        "tier": "gold",
        "category": "reward",
    },
    # 連続系
    {
        "id": "streak10",
        "name": "10連勝",
        "desc": "10回連続でタスク成功",
        "tier": "silver",
        "category": "streak",
    },
    {
        "id": "streak50",
        "name": "50連勝",
        "desc": "50回連続でタスク成功",
        "tier": "legend",
        "category": "streak",
    },
]

# クエスト定義
QUESTS_DEF = [
    {
        "id": "quest_shadow50",
        "title": "Shadow 50試行",
        "desc": "夜間に安全試行を50回完了する",
        "type": "trial_count",
        "target": 50,
        "reward": "achievement:shadow50",
        "expires": None,  # None = 無期限
    },
    {
        "id": "quest_reward5",
        "title": "ΔReward +5%",
        "desc": "ベースライン比+5%を達成",
        "type": "reward_delta",
        "target": 0.05,
        "reward": "achievement:reward5",
        "expires": None,
    },
    {
        "id": "quest_trust90",
        "title": "信頼度 90%維持",
        "desc": "confidence 0.90を3時間維持",
        "type": "trust_maintain",
        "target": 0.90,
        "duration_hours": 3,
        "reward": "achievement:trust90",
        "expires": None,
    },
    {
        "id": "quest_slo",
        "title": "SLO遵守",
        "desc": "p95 ≤ 3000ms を維持",
        "type": "latency_under",
        "target": 3000,
        "reward": "achievement:slo1",
        "expires": None,
    },
    {
        "id": "quest_daily_trials",
        "title": "デイリートライアル",
        "desc": "1日で20回以上の試行を完了",
        "type": "daily_trial_count",
        "target": 20,
        "reward": "achievement:shadow50",
        "expires": 24,  # 24時間で期限切れ
    },
]

class AchievementChecker:
    """実績チェッカー"""

    def __init__(self, context_provider: Callable[[], Dict[str, Any]]):
        """
        :param context_provider: コンテキスト取得関数（進化状態、統計等を返す）
        """
        self.context_provider = context_provider

    def check_all(self) -> List[Dict[str, Any]]:
        """全実績をチェックして獲得済みでないものを返す"""
        context = self.context_provider()
        earned = []

        for ach_def in ACHIEVEMENTS_DEF:
            # 既に獲得済みかチェック
            if any(a.get("id") == ach_def["id"] for a in context.get("achievements", [])):
                continue

            # 条件チェック
            if self._check_achievement(ach_def, context):
                earned.append({
                    **ach_def,
                    "earnedAt": datetime.now().isoformat(),
                })

        return earned

    def _check_achievement(self, ach_def: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """個別実績のチェック"""
        ach_id = ach_def["id"]

        # 速度系
        if ach_id == "fast0":
            # A→C同日達成（簡易版: Stage Cが完了している）
            stages = context.get("stages", [])
            stage_c_done = any(s.get("id") == "C" and s.get("done") for s in stages)
            return stage_c_done

        if ach_id == "fast1":
            # 1日でStage実装（簡易版）
            return True  # 仮実装

        # 安全系
        if ach_id == "safe1":
            # KillSwitch実装済み（簡易版）
            return True  # 既に実装済み

        if ach_id == "safe2":
            # 緊急停止10回以上（要統計）
            emergency_count = context.get("emergency_stop_count", 0)
            return emergency_count >= 10

        # 監視系
        if ach_id == "ops1":
            # メトリクス10種以上（簡易版）
            return True  # 既に実装済み

        if ach_id == "ops2":
            # 1日で100回以上のメトリクス収集（要統計）
            metrics_today = context.get("metrics_collected_today", 0)
            return metrics_today >= 100

        # 試行系
        if ach_id == "shadow50":
            trials = context.get("trials_today", 0)
            mode = context.get("mode", "off")
            return mode == "shadow" and trials >= 50

        if ach_id == "shadow100":
            trials_total = context.get("total_trials", 0)
            return trials_total >= 100

        if ach_id == "canary10":
            mode = context.get("mode", "off")
            canary_ratio = context.get("canary_ratio", 0)
            return mode == "canary" and canary_ratio >= 0.1

        # 信頼度系
        if ach_id == "trust90":
            confidence = context.get("confidence", 0.0)
            return confidence >= 0.90

        if ach_id == "trust95":
            confidence = context.get("confidence", 0.0)
            return confidence >= 0.95

        # パフォーマンス系
        if ach_id == "slo1":
            p95 = context.get("p95", float('inf'))
            return p95 <= 3000

        if ach_id == "slo2":
            p95 = context.get("p95", float('inf'))
            return p95 <= 1000

        # 報酬系
        if ach_id == "reward5":
            best_variant = context.get("bestVariant")
            if best_variant:
                return best_variant.get("deltaReward", 0) >= 0.05
            return False

        if ach_id == "reward10":
            best_variant = context.get("bestVariant")
            if best_variant:
                return best_variant.get("deltaReward", 0) >= 0.10
            return False

        # 連続系
        if ach_id == "streak10":
            streak = context.get("success_streak", 0)
            return streak >= 10

        if ach_id == "streak50":
            streak = context.get("success_streak", 0)
            return streak >= 50

        return False

class QuestManager:
    """クエスト管理"""

    def __init__(self, context_provider: Callable[[], Dict[str, Any]]):
        self.context_provider = context_provider
        self.active_quests: List[Dict[str, Any]] = []

    def get_active_quests(self) -> List[Dict[str, Any]]:
        """アクティブなクエスト一覧"""
        context = self.context_provider()

        active = []
        for quest_def in QUESTS_DEF:
            # 期限チェック
            if quest_def.get("expires"):
                # 期限切れチェック（簡易版）
                pass

            # 進行状況計算
            progress = self._calculate_progress(quest_def, context)
            done = progress >= quest_def["target"]

            active.append({
                **quest_def,
                "progress": progress,
                "done": done,
            })

        return active

    def _calculate_progress(self, quest_def: Dict[str, Any], context: Dict[str, Any]) -> float:
        """クエストの進行状況を計算"""
        quest_type = quest_def["type"]

        if quest_type == "trial_count":
            return float(context.get("trials_today", 0))

        if quest_type == "reward_delta":
            best_variant = context.get("bestVariant")
            if best_variant:
                return best_variant.get("deltaReward", 0)
            return 0.0

        if quest_type == "trust_maintain":
            confidence = context.get("confidence", 0.0)
            return confidence

        if quest_type == "latency_under":
            p95 = context.get("p95", float('inf'))
            # 目標値以下の場合、進捗100%
            return 1.0 if p95 <= quest_def["target"] else 0.0

        if quest_type == "daily_trial_count":
            return float(context.get("trials_today", 0))

        return 0.0





