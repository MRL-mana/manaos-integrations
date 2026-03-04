"""
Evolution Engine - 進化モード管理・Reward計算・Variant管理
"""

import json
import os
from typing import Dict, Any, List, Optional, Literal
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from ai_simulator.core.achievements import AchievementChecker, QuestManager

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/evolution"))
EVOLUTION_STATE_FILE = DATA_DIR / "evolution_state.json"
VARIANTS_FILE = DATA_DIR / "variants.json"
REWARD_HISTORY_FILE = DATA_DIR / "reward_history.json"
ACHIEVEMENTS_FILE = DATA_DIR / "achievements.json"

class EvolutionEngine:
    """進化エンジン"""

    def __init__(self):
        self.mode: Literal["off", "shadow", "canary", "live"] = "off"
        self.trust = 70.0  # 0-100
        self.confidence = 0.7  # 0-1
        self.canary_ratio = 0.1  # 0-1
        self.trials_today = 0
        self.p95 = 0.0  # ms
        self.cost = 5.0  # JPY per success
        self.reward_history: List[Dict[str, Any]] = []
        self.variants: Dict[str, Dict[str, Any]] = {}
        self.achievements: List[Dict[str, Any]] = []
        self.policy = {
            "success_rate": 0.35,
            "latency_gain": 0.2,
            "error_drop": 0.2,
            "human_feedback": 0.1,
            "reproducibility": 0.1,
            "cost_efficiency": 0.05,
            "hard_slo_ms": 3000,
            "trust_gate": 0.7,
            "promote_delta": 0.05,
        }

        self.load_state()
        self._calculate_metrics()

        # Achievement/Quest システム初期化（循環参照を避けるため、内部メソッドでコンテキスト取得）
        self.achievement_checker = AchievementChecker(self._get_context_for_achievements)
        self.quest_manager = QuestManager(self._get_context_for_achievements)

    def load_state(self):
        """状態を読み込む"""
        # Evolution状態
        if EVOLUTION_STATE_FILE.exists():
            try:
                with open(EVOLUTION_STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.mode = state.get("mode", "off")
                    self.trust = state.get("trust", 70.0)
                    self.confidence = state.get("confidence", 0.7)
                    self.canary_ratio = state.get("canary_ratio", 0.1)
                    self.trials_today = state.get("trials_today", 0)
            except Exception as e:
                logger.error(f"Failed to load evolution state: {e}")

        # バリアント
        if VARIANTS_FILE.exists():
            try:
                with open(VARIANTS_FILE, "r", encoding="utf-8") as f:
                    self.variants = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load variants: {e}")

        # 報酬履歴
        if REWARD_HISTORY_FILE.exists():
            try:
                with open(REWARD_HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.reward_history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load reward history: {e}")

        # 実績
        if ACHIEVEMENTS_FILE.exists():
            try:
                with open(ACHIEVEMENTS_FILE, "r", encoding="utf-8") as f:
                    self.achievements = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load achievements: {e}")

    def save_state(self):
        """状態を保存"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with open(EVOLUTION_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "mode": self.mode,
                    "trust": self.trust,
                    "confidence": self.confidence,
                    "canary_ratio": self.canary_ratio,
                    "trials_today": self.trials_today,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save evolution state: {e}")

        try:
            with open(VARIANTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.variants, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save variants: {e}")

        try:
            with open(REWARD_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.reward_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save reward history: {e}")

        try:
            with open(ACHIEVEMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.achievements, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save achievements: {e}")

    def start_mode(self, mode: Literal["shadow", "canary", "live"]):
        """進化モード開始"""
        self.mode = mode
        self.save_state()
        logger.info(f"Evolution mode started: {mode}")

    def stop(self):
        """進化モード停止"""
        self.mode = "off"
        self.save_state()
        logger.info("Evolution mode stopped")

    def set_canary_ratio(self, ratio: float):
        """Canary比率設定"""
        self.canary_ratio = max(0.05, min(0.5, ratio))
        self.save_state()

    def set_policy(self, policy: Dict[str, Any]):
        """ポリシー設定"""
        self.policy.update(policy)
        self.save_state()

    def record_trial(self, variant_id: str, success: bool, latency_ms: float,
                     cost: float = 0.0):
        """試行記録"""
        if self.mode == "off":
            return

        self.trials_today += 1

        # バリアント統計更新
        if variant_id not in self.variants:
            self.variants[variant_id] = {
                "id": variant_id,
                "success_count": 0,
                "failure_count": 0,
                "total_latency": 0.0,
                "total_cost": 0.0,
                "trial_count": 0,
            }

        v = self.variants[variant_id]
        v["trial_count"] += 1
        if success:
            v["success_count"] += 1
        else:
            v["failure_count"] += 1
        v["total_latency"] += latency_ms
        v["total_cost"] += cost

        # 報酬計算
        reward = self._calculate_reward(success, latency_ms, cost)

        # 報酬履歴追加（時間ごとに集約）
        now = datetime.now()
        hour_key = now.strftime("%H:00")

        # 直近24時間分を保持
        self.reward_history.append({
            "t": hour_key,
            "reward": reward,
            "success": 1.0 if success else 0.0,
            "p95": latency_ms,
            "timestamp": now.isoformat(),
        })

        # 古いデータを削除（24時間以上前）
        cutoff = now - timedelta(hours=24)
        self.reward_history = [
            r for r in self.reward_history
            if datetime.fromisoformat(r["timestamp"]) >= cutoff
        ]

        # 信頼度・Trust更新
        self._update_confidence_trust(success, latency_ms)

        # 実績チェック
        self._check_achievements()

        self.save_state()

    def _calculate_reward(self, success: bool, latency_ms: float, cost: float) -> float:
        """報酬を計算"""
        reward = 0.0

        # Success rate
        if success:
            reward += self.policy["success_rate"]

        # Latency gain（低遅延ほど高得点）
        if latency_ms < self.policy["hard_slo_ms"]:
            latency_score = 1.0 - (latency_ms / self.policy["hard_slo_ms"])
            reward += self.policy["latency_gain"] * latency_score

        # Cost efficiency
        if cost > 0:
            cost_score = max(0, 1.0 - (cost / 10.0))  # 10円以下を理想とする
            reward += self.policy["cost_efficiency"] * cost_score

        return min(1.0, reward)

    def _update_confidence_trust(self, success: bool, latency_ms: float):
        """信頼度・Trust更新"""
        # 信頼度更新（成功で+0.01、失敗で-0.02）
        if success:
            self.confidence = min(1.0, self.confidence + 0.01)
        else:
            self.confidence = max(0.0, self.confidence - 0.02)

        # Trust更新（信頼度ベース、SLO遵守でボーナス）
        trust_base = self.confidence * 100
        slo_bonus = 5.0 if latency_ms <= self.policy["hard_slo_ms"] else 0.0
        self.trust = min(100.0, max(0.0, trust_base + slo_bonus))

    def _calculate_metrics(self):
        """メトリクス計算（p95, cost等）"""
        if not self.reward_history:
            return

        # p95計算
        latencies = [r["p95"] for r in self.reward_history[-100:]]  # 直近100件
        latencies.sort()
        self.p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        # Cost計算（簡易版）
        self.cost = 5.0 + (self.p95 / 1000) * 0.5  # 仮計算

    def get_best_variant(self) -> Optional[Dict[str, Any]]:
        """最良バリアント取得"""
        if not self.variants:
            return None

        best = None
        best_delta = 0.0

        for variant_id, v in self.variants.items():
            if v["trial_count"] < 5:  # 最小試行数
                continue

            success_rate = v["success_count"] / v["trial_count"]
            avg_latency = v["total_latency"] / v["trial_count"]
            reward = self._calculate_reward(success_rate > 0.9, avg_latency, v["total_cost"] / v["trial_count"])

            # ベースラインとの差分（簡易版）
            delta_reward = reward - 0.5  # ベースライン0.5と仮定

            if delta_reward > best_delta:
                best_delta = delta_reward
                best = {
                    "id": variant_id,
                    "deltaReward": delta_reward,
                    "confidence": success_rate,
                }

        return best

    def promote_variant(self, variant_id: str):
        """バリアント昇格"""
        if variant_id not in self.variants:
            raise ValueError(f"Variant {variant_id} not found")

        # Canary → Live への昇格
        if self.mode == "canary":
            self.mode = "live"
            self.canary_ratio = 1.0
            self.save_state()
            logger.info(f"Variant {variant_id} promoted to live")

    def _get_context_for_achievements(self) -> Dict[str, Any]:
        """Achievement/Quest用のコンテキスト取得（循環参照回避）"""
        return {
            "mode": self.mode,
            "trust": self.trust,
            "confidence": self.confidence,
            "p95": self.p95,
            "cost": self.cost,
            "canary_ratio": self.canary_ratio,
            "trials_today": self.trials_today,
            "stages": [
                {"id": "A", "name": "Stage A – 観測", "done": True},
                {"id": "B", "name": "Stage B – 制御統合", "done": True},
                {"id": "C", "name": "Stage C – フル連携", "done": True},
                {"id": "D", "name": "Stage D – Reflexive", "done": False},
                {"id": "E", "name": "Stage E – Vision", "done": False},
            ],
            "bestVariant": self.get_best_variant(),
            "achievements": self.achievements,
            "emergency_stop_count": 0,  # TODO: 統計から取得
            "metrics_collected_today": 0,  # TODO: 統計から取得
            "total_trials": self.trials_today,  # TODO: 累計から取得
            "success_streak": 0,  # TODO: 統計から取得
        }

    def _check_achievements(self):
        """実績チェック"""
        earned = self.achievement_checker.check_all()

        for ach in earned:
            self.achievements.append(ach)
            logger.info(f"Achievement unlocked: {ach['name']}")

    def get_status(self) -> Dict[str, Any]:
        """状態取得"""
        self._calculate_metrics()

        # Reward履歴を時間ごとに集約
        reward_by_hour = defaultdict(lambda: {"reward": [], "success": [], "p95": []})
        for r in self.reward_history:
            hour = r["t"]
            reward_by_hour[hour]["reward"].append(r["reward"])
            reward_by_hour[hour]["success"].append(r["success"])
            reward_by_hour[hour]["p95"].append(r["p95"])

        reward_history_aggregated = []
        for hour in sorted(reward_by_hour.keys())[-24:]:  # 直近24時間
            data = reward_by_hour[hour]
            reward_history_aggregated.append({
                "t": hour,
                "reward": sum(data["reward"]) / len(data["reward"]) if data["reward"] else 0.0,
                "success": sum(data["success"]) / len(data["success"]) if data["success"] else 0.0,
                "p95": sorted(data["p95"])[int(len(data["p95"]) * 0.95)] if data["p95"] else 0.0,
            })

        # Stage情報（Vision Mode状態も反映）
        try:
            from ai_simulator.core.vision_mode import VisionMode
            vision = VisionMode()
            vision_summary = vision.get_strategic_summary()
            vision_done = vision_summary["active_goals_count"] > 0 or vision_summary["completed_goals_count"] > 0
        except Exception:
            vision_done = False

        stages = [
            {"id": "A", "name": "Stage A – 観測", "done": True},
            {"id": "B", "name": "Stage B – 制御統合", "done": True},
            {"id": "C", "name": "Stage C – フル連携", "done": True},
            {"id": "D", "name": "Stage D – Reflexive", "done": True},  # 最小実装完了
            {"id": "E", "name": "Stage E – Vision", "done": vision_done},
        ]

        return {
            "mode": self.mode,
            "trust": self.trust,
            "confidence": self.confidence,
            "p95": self.p95,
            "cost": self.cost,
            "canary_ratio": self.canary_ratio,
            "trials_today": self.trials_today,
            "reward_history": reward_history_aggregated,
            "stages": stages,
            "achievements": self.achievements,
            "quests": self.quest_manager.get_active_quests(),
            "bestVariant": self.get_best_variant(),
        }

    def get_quests(self) -> List[Dict[str, Any]]:
        """アクティブなクエスト一覧取得"""
        return self.quest_manager.get_active_quests()

# グローバルインスタンス
evolution_engine = EvolutionEngine()

