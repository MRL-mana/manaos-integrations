"""
Auto-Curriculum — リプレイバッファ + アナリティクスから自動難易度調整
======================================================================
過去のパフォーマンストレンドを分析し、最適な難易度レベルを推薦。
従来の固定ルールに加え、スライディングウィンドウの移動平均・傾き・
安定度を考慮した適応的カリキュラムを実現する。

使い方:
  ac = AutoCurriculum(config)
  recommendation = ac.recommend(history, replay_stats)
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .types import DifficultyLevel


# ─────────────── 推薦結果 ───────────────
@dataclass
class CurriculumRecommendation:
    """カリキュラム推薦結果"""
    recommended: DifficultyLevel
    current: DifficultyLevel
    changed: bool
    confidence: float  # 0.0 – 1.0
    reasoning: str
    signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "recommended": self.recommended.value,
            "current": self.current.value,
            "changed": self.changed,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "signals": self.signals,
        }


# ─────────────── レベル順序表 ───────────────
_LEVELS = [DifficultyLevel.CONCRETE, DifficultyLevel.GUIDED,
           DifficultyLevel.STANDARD, DifficultyLevel.ABSTRACT]
_LEVEL_IDX = {lv: i for i, lv in enumerate(_LEVELS)}


def _level_up(current: DifficultyLevel) -> DifficultyLevel:
    i = _LEVEL_IDX[current]
    return _LEVELS[min(i + 1, len(_LEVELS) - 1)]


def _level_down(current: DifficultyLevel) -> DifficultyLevel:
    i = _LEVEL_IDX[current]
    return _LEVELS[max(i - 1, 0)]


class AutoCurriculum:
    """
    適応的カリキュラムエンジン。

    判定ロジック:
    1) 直近 N サイクルの成功率 & 平均スコア
    2) スコア移動平均の傾き (上昇トレンド → レベルアップ候補)
    3) スコアの分散 (高分散 = まだ安定していない → ステイ)
    4) 連続成功/失敗ストリーク
    5) リプレイバッファの failure 比率
    """

    # デフォルトパラメータ
    WINDOW_SIZE = 10
    UP_THRESHOLD = 0.75       # 成功率この値以上 → level up 検討
    DOWN_THRESHOLD = 0.30     # 成功率この値以下 → level down 検討
    MIN_SCORE_FOR_UP = 0.65   # 平均スコアもこの値以上必要
    STABILITY_THRESHOLD = 0.20  # stddev がこれ以下で「安定」
    STREAK_TRIGGER = 4        # 連続成功/失敗で即判定
    TREND_SLOPE_UP = 0.02     # 傾きこの値以上 → 上昇トレンド
    TREND_SLOPE_DOWN = -0.03  # 傾きこの値以下 → 下降トレンド

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        cur_cfg = cfg.get("curriculum", {})
        self.window_size = cur_cfg.get("window_size", self.WINDOW_SIZE)
        self.up_threshold = cur_cfg.get("up_threshold", self.UP_THRESHOLD)
        self.down_threshold = cur_cfg.get("down_threshold", self.DOWN_THRESHOLD)
        self.min_score_up = cur_cfg.get("min_score_for_up", self.MIN_SCORE_FOR_UP)
        self.stability_thr = cur_cfg.get("stability_threshold", self.STABILITY_THRESHOLD)
        self.streak_trigger = cur_cfg.get("streak_trigger", self.STREAK_TRIGGER)

    def recommend(
        self,
        history: List[Dict[str, Any]],
        current_difficulty: DifficultyLevel,
        replay_stats: Optional[Dict[str, Any]] = None,
    ) -> CurriculumRecommendation:
        """
        履歴 (metrics.jsonl entries) + 現在の難易度から推薦を算出。
        """
        if len(history) < 3:
            return CurriculumRecommendation(
                recommended=current_difficulty,
                current=current_difficulty,
                changed=False,
                confidence=0.0,
                reasoning="データ不足 (最低3サイクル必要)",
            )

        window = history[-self.window_size:]
        signals = self._compute_signals(window, replay_stats)
        decision, confidence, reasoning = self._decide(
            signals, current_difficulty
        )

        return CurriculumRecommendation(
            recommended=decision,
            current=current_difficulty,
            changed=(decision != current_difficulty),
            confidence=confidence,
            reasoning=reasoning,
            signals=signals,
        )

    def _compute_signals(
        self, window: List[Dict[str, Any]], replay_stats: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """ウィンドウ内の統計シグナルを算出"""
        outcomes = [e.get("outcome", "unknown") for e in window]
        scores = [e.get("score", 0.0) for e in window]
        n = len(window)

        # 基本統計
        success_count = sum(1 for o in outcomes if o == "success")
        failure_count = sum(1 for o in outcomes if o == "failure")
        success_rate = success_count / n if n else 0
        avg_score = sum(scores) / n if n else 0
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0

        # 傾き (最小二乗法)
        slope = self._compute_slope(scores)

        # 連続ストリーク
        success_streak = self._count_streak(outcomes, "success")
        failure_streak = self._count_streak(outcomes, "failure")

        # リプレイバッファの failure 比率
        replay_failure_rate = 0.0
        if replay_stats:
            dist = replay_stats.get("outcome_distribution", {})
            total = sum(dist.values())
            if total > 0:
                replay_failure_rate = dist.get("failure", 0) / total

        return {
            "success_rate": round(success_rate, 4),
            "failure_rate": round(failure_count / n if n else 0, 4),
            "avg_score": round(avg_score, 4),
            "score_std": round(score_std, 4),
            "slope": round(slope, 6),
            "success_streak": success_streak,
            "failure_streak": failure_streak,
            "sample_size": n,
            "replay_failure_rate": round(replay_failure_rate, 4),
        }

    def _decide(
        self, signals: Dict[str, Any], current: DifficultyLevel
    ) -> Tuple[DifficultyLevel, float, str]:
        """シグナルから難易度変更の判定"""
        sr = signals["success_rate"]
        avg = signals["avg_score"]
        std = signals["score_std"]
        slope = signals["slope"]
        s_streak = signals["success_streak"]
        f_streak = signals["failure_streak"]
        reasons = []

        # ──── 即時判定: ストリーク ────
        if f_streak >= self.streak_trigger:
            new = _level_down(current)
            return new, 0.9, f"連続失敗 {f_streak}回 → レベルダウン"

        if s_streak >= self.streak_trigger and avg >= self.min_score_up:
            new = _level_up(current)
            return new, 0.85, f"連続成功 {s_streak}回 (avg={avg:.2f}) → レベルアップ"

        # ──── 成功率ベース判定 ────
        confidence = 0.5
        decision = current

        if sr >= self.up_threshold and avg >= self.min_score_up:
            if std <= self.stability_thr:
                # 高成功率 & 高スコア & 安定 → レベルアップ
                decision = _level_up(current)
                confidence = min(0.95, 0.6 + sr * 0.3)
                reasons.append(f"高成功率({sr:.0%}) & 安定(σ={std:.3f})")
            elif slope >= self.TREND_SLOPE_UP:
                # 安定はしていないが上昇トレンド → 控えめにアップ
                decision = _level_up(current)
                confidence = 0.55
                reasons.append(f"上昇トレンド(slope={slope:.4f}) ただし分散大(σ={std:.3f})")
            else:
                reasons.append(f"高成功率だが不安定(σ={std:.3f}) → ステイ")

        elif sr <= self.down_threshold:
            decision = _level_down(current)
            confidence = min(0.9, 0.5 + (1 - sr) * 0.4)
            reasons.append(f"低成功率({sr:.0%}) → レベルダウン")

        else:
            # 中間帯: トレンドで微調整
            if slope <= self.TREND_SLOPE_DOWN and avg < 0.5:
                decision = _level_down(current)
                confidence = 0.5
                reasons.append(f"下降トレンド(slope={slope:.4f}, avg={avg:.2f})")
            elif slope >= self.TREND_SLOPE_UP and avg >= 0.6:
                decision = _level_up(current)
                confidence = 0.45
                reasons.append(f"上昇トレンド(slope={slope:.4f}, avg={avg:.2f})")
            else:
                reasons.append(f"安定圏内(sr={sr:.0%}, avg={avg:.2f}) → ステイ")

        reasoning = "; ".join(reasons) if reasons else "変化なし"
        return decision, confidence, reasoning

    @staticmethod
    def _compute_slope(values: List[float]) -> float:
        """最小二乗法で傾き (1次フィット) を算出"""
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _count_streak(outcomes: List[str], target: str) -> int:
        """末尾からの連続 target カウント"""
        streak = 0
        for o in reversed(outcomes):
            if o == target:
                streak += 1
            else:
                break
        return streak
