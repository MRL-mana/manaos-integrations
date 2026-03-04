"""
Reward Shaper — ポテンシャルベース報酬整形
================================================================
生のタスクスコアを動的に変換し、学習効率を向上させる。

手法:
  1) Potential-Based Reward Shaping (PBRS)
     - Φ(s) = 状態ポテンシャル関数
     - F(s,s') = γ·Φ(s') - Φ(s)
     - shaped_reward = raw_reward + F

  2) Curiosity Bonus
     - 訪問頻度の逆数に基づく探索ボーナス

  3) Difficulty Scaling
     - 高難易度での成功により大きな報酬

  4) Consistency Bonus
     - 安定したパフォーマンスにボーナス

理論保証: PBRS は最適方策を変えない（Ng+ 1999）
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


DIFFICULTIES = ["concrete", "guided", "standard", "abstract"]
DIFF_IDX = {d: i for i, d in enumerate(DIFFICULTIES)}


@dataclass
class ShapedReward:
    """整形後の報酬とその内訳"""
    raw: float
    shaped: float
    potential_bonus: float
    curiosity_bonus: float
    difficulty_bonus: float
    consistency_bonus: float
    components: Dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


class RewardShaper:
    """
    動的報酬整形エンジン。
    generate() で生スコアを変換、内訳も返す。
    """

    # PBRS ディスカウント
    GAMMA = 0.99

    # Curiosity
    CURIOSITY_SCALE = 0.05
    CURIOSITY_DECAY = 0.999  # 訪問カウンタの減衰

    # Difficulty scaling
    DIFFICULTY_MULTIPLIER = {
        "concrete": 0.85,
        "guided": 0.95,
        "standard": 1.00,
        "abstract": 1.15,
    }

    # Consistency
    CONSISTENCY_WINDOW = 5
    CONSISTENCY_THRESHOLD = 0.1  # std < threshold でボーナス
    CONSISTENCY_BONUS_MAX = 0.05

    # 上下限クランプ
    MIN_SHAPED = 0.0
    MAX_SHAPED = 1.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}

        # ポテンシャル関数のパラメータ
        self._potential_weight = cfg.get("potential_weight", 0.1)
        self._curiosity_enabled = cfg.get("curiosity_enabled", True)

        # 状態訪問カウンタ (difficulty × outcome)
        self._visit_counts: Dict[str, int] = defaultdict(int)
        self._total_visits: int = 0

        # 直近スコア履歴（consistency 計算用）
        self._score_history: List[float] = []
        self._max_history = 100

        # 前回の状態ポテンシャル（PBRS 差分計算用）
        self._prev_potential: float = 0.0

    # ═══════════════════════════════════════════════════════
    # メイン: 報酬整形
    # ═══════════════════════════════════════════════════════
    def shape(
        self,
        raw_score: float,
        outcome: str,
        difficulty: str,
        success_rate: float = 0.5,
        avg_score: float = 0.5,
    ) -> ShapedReward:
        """
        生スコアを整形して ShapedReward を返す。

        Args:
            raw_score: 元のタスクスコア (0-1)
            outcome: success / failure / partial / unknown
            difficulty: 難易度レベル
            success_rate: 直近の成功率
            avg_score: 直近の平均スコア
        """
        # 状態キー
        state_key = f"{difficulty}:{outcome}"
        self._visit_counts[state_key] += 1
        self._total_visits += 1

        # 1) Potential-Based Reward Shaping
        current_potential = self._compute_potential(success_rate, avg_score, difficulty)
        pbrs_bonus = self.GAMMA * current_potential - self._prev_potential
        pbrs_bonus *= self._potential_weight
        self._prev_potential = current_potential

        # 2) Curiosity Bonus
        curiosity = 0.0
        if self._curiosity_enabled:
            visit_count = self._visit_counts[state_key]
            curiosity = self.CURIOSITY_SCALE / math.sqrt(max(visit_count, 1))

        # 3) Difficulty Scaling
        diff_mult = self.DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)
        diff_bonus = raw_score * (diff_mult - 1.0)

        # 4) Consistency Bonus
        self._score_history.append(raw_score)
        if len(self._score_history) > self._max_history:
            self._score_history = self._score_history[-self._max_history:]

        consistency = 0.0
        if len(self._score_history) >= self.CONSISTENCY_WINDOW:
            recent = self._score_history[-self.CONSISTENCY_WINDOW:]
            std = statistics.stdev(recent) if len(recent) > 1 else 0.0
            if std < self.CONSISTENCY_THRESHOLD:
                consistency = self.CONSISTENCY_BONUS_MAX * (1.0 - std / self.CONSISTENCY_THRESHOLD)

        # 合算
        shaped = raw_score + pbrs_bonus + curiosity + diff_bonus + consistency
        shaped = max(self.MIN_SHAPED, min(self.MAX_SHAPED, shaped))

        return ShapedReward(
            raw=round(raw_score, 4),
            shaped=round(shaped, 4),
            potential_bonus=round(pbrs_bonus, 4),
            curiosity_bonus=round(curiosity, 4),
            difficulty_bonus=round(diff_bonus, 4),
            consistency_bonus=round(consistency, 4),
            components={
                "raw": round(raw_score, 4),
                "pbrs": round(pbrs_bonus, 4),
                "curiosity": round(curiosity, 4),
                "difficulty": round(diff_bonus, 4),
                "consistency": round(consistency, 4),
            },
        )

    # ═══════════════════════════════════════════════════════
    # ポテンシャル関数
    # ═══════════════════════════════════════════════════════
    def _compute_potential(
        self,
        success_rate: float,
        avg_score: float,
        difficulty: str,
    ) -> float:
        """
        状態ポテンシャル Φ(s)。

        高い成功率 + 高スコア + 高難易度 → 高ポテンシャル
        """
        diff_idx = DIFF_IDX.get(difficulty, 2)
        diff_norm = diff_idx / 3.0

        # 重み付き合計
        return (
            0.4 * success_rate
            + 0.4 * avg_score
            + 0.2 * diff_norm
        )

    # ═══════════════════════════════════════════════════════
    # バッチ整形
    # ═══════════════════════════════════════════════════════
    def shape_batch(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[ShapedReward]:
        """複数経験を一括整形"""
        results = []
        for exp in experiences:
            sr = self.shape(
                raw_score=exp.get("score", 0),
                outcome=exp.get("outcome", "unknown"),
                difficulty=exp.get("difficulty", "standard"),
                success_rate=exp.get("success_rate", 0.5),
                avg_score=exp.get("avg_score", 0.5),
            )
            results.append(sr)
        return results

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """現在の状態統計"""
        recent = self._score_history[-20:]
        avg = sum(recent) / len(recent) if recent else 0

        # 訪問分布
        visit_dist = dict(self._visit_counts)

        return {
            "total_visits": self._total_visits,
            "visit_distribution": visit_dist,
            "score_history_len": len(self._score_history),
            "recent_avg_score": round(avg, 4),
            "current_potential": round(self._prev_potential, 4),
            "curiosity_enabled": self._curiosity_enabled,
        }

    def reset(self) -> None:
        """状態をリセット"""
        self._visit_counts.clear()
        self._total_visits = 0
        self._score_history.clear()
        self._prev_potential = 0.0
