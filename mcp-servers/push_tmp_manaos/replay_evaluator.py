"""
Replay Evaluator — 過去の経験を再評価して学習の質を向上
================================================================
リプレイバッファからサンプルし、更新されたスコアリング基準で
再評価することで、過去の判断を振り返り改善する。

機能:
  1) re-score: 新しいスコアリング基準でスコアを再計算
  2) drift detection: 新旧スコアの乖離を検出
  3) insight extraction: 再評価結果からパターンを抽出
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .replay_buffer import Experience, ReplayBuffer


@dataclass
class ReEvalResult:
    """再評価結果"""
    task_id: str
    original_score: float
    new_score: float
    drift: float               # new - original
    outcome: str
    difficulty: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "original_score": round(self.original_score, 4),
            "new_score": round(self.new_score, 4),
            "drift": round(self.drift, 4),
            "outcome": self.outcome,
            "difficulty": self.difficulty,
            "reason": self.reason,
        }


@dataclass
class ReEvalReport:
    """再評価レポート"""
    total_evaluated: int
    avg_drift: float
    positive_drift_count: int    # 新基準で評価が上がった
    negative_drift_count: int    # 新基準で評価が下がった
    zero_drift_count: int
    max_positive_drift: float
    max_negative_drift: float
    drift_by_outcome: Dict[str, float]
    drift_by_difficulty: Dict[str, float]
    results: List[ReEvalResult]
    insights: List[str]

    def to_dict(self) -> dict:
        return {
            "total_evaluated": self.total_evaluated,
            "avg_drift": round(self.avg_drift, 4),
            "positive_drift_count": self.positive_drift_count,
            "negative_drift_count": self.negative_drift_count,
            "zero_drift_count": self.zero_drift_count,
            "max_positive_drift": round(self.max_positive_drift, 4),
            "max_negative_drift": round(self.max_negative_drift, 4),
            "drift_by_outcome": {k: round(v, 4) for k, v in self.drift_by_outcome.items()},
            "drift_by_difficulty": {k: round(v, 4) for k, v in self.drift_by_difficulty.items()},
            "results": [r.to_dict() for r in self.results],
            "insights": self.insights,
        }


class ReplayEvaluator:
    """
    リプレイバッファの経験を再評価するエンジン。

    scoring_criteria: {criterion: weight, ...}
    各経験のスコアを outcome ベースラインに criteria 重みで調整。
    """

    # Outcome ベーススコア
    BASE_SCORES = {
        "success": 0.75,
        "partial": 0.50,
        "failure": 0.20,
        "unknown": 0.40,
    }

    def __init__(self, scoring_criteria: Optional[Dict[str, float]] = None):
        self.scoring_criteria = scoring_criteria or {}

    def re_score(self, exp: Experience) -> float:
        """
        新しい基準でスコアを再計算。
        ベーススコア + ツール/エラー調整 + 難易度ボーナス。
        """
        base = self.BASE_SCORES.get(exp.outcome, 0.4)

        # エラー率で減点
        if exp.tool_count > 0:
            error_ratio = exp.error_count / exp.tool_count
            base -= error_ratio * 0.25

        # ツール数の適正範囲
        if exp.tool_count <= 2:
            base -= 0.05
        elif exp.tool_count > 30:
            base -= 0.10

        # 難易度ボーナス (abstract で成功は追加点)
        diff_bonus = {
            "abstract": 0.10,
            "standard": 0.05,
            "guided": 0.0,
            "concrete": -0.05,
        }
        if exp.outcome == "success":
            base += diff_bonus.get(exp.difficulty, 0)

        # スキル使用ボーナス
        if len(exp.skills_used) >= 2:
            base += 0.05

        return round(max(0.0, min(1.0, base)), 4)

    def evaluate_batch(
        self,
        experiences: List[Experience],
        prioritized: bool = False,
    ) -> ReEvalReport:
        """
        バッチ再評価 → 統計レポート生成
        """
        results: List[ReEvalResult] = []
        drift_by_outcome: Dict[str, List[float]] = defaultdict(list)
        drift_by_diff: Dict[str, List[float]] = defaultdict(list)

        for exp in experiences:
            new_score = self.re_score(exp)
            drift = new_score - exp.score
            reason = self._explain_drift(exp, new_score, drift)

            results.append(ReEvalResult(
                task_id=exp.task_id,
                original_score=exp.score,
                new_score=new_score,
                drift=drift,
                outcome=exp.outcome,
                difficulty=exp.difficulty,
                reason=reason,
            ))
            drift_by_outcome[exp.outcome].append(drift)
            drift_by_diff[exp.difficulty].append(drift)

        # 統計
        drifts = [r.drift for r in results]
        n = len(results)
        avg_drift = sum(drifts) / n if n else 0
        pos = sum(1 for d in drifts if d > 0.01)
        neg = sum(1 for d in drifts if d < -0.01)
        zero = n - pos - neg

        # Outcome 別平均ドリフト
        outcome_avg = {
            k: sum(v) / len(v) if v else 0
            for k, v in drift_by_outcome.items()
        }
        diff_avg = {
            k: sum(v) / len(v) if v else 0
            for k, v in drift_by_diff.items()
        }

        # インサイト抽出
        insights = self._extract_insights(results, outcome_avg, diff_avg, avg_drift)

        return ReEvalReport(
            total_evaluated=n,
            avg_drift=avg_drift,
            positive_drift_count=pos,
            negative_drift_count=neg,
            zero_drift_count=zero,
            max_positive_drift=max(drifts) if drifts else 0,
            max_negative_drift=min(drifts) if drifts else 0,
            drift_by_outcome=outcome_avg,
            drift_by_difficulty=diff_avg,
            results=results,
            insights=insights,
        )

    def evaluate_buffer(
        self,
        replay: ReplayBuffer,
        sample_size: int = 50,
        prioritized: bool = True,
    ) -> ReEvalReport:
        """
        リプレイバッファからサンプリングして再評価。
        """
        if replay.size == 0:
            return ReEvalReport(
                total_evaluated=0, avg_drift=0, positive_drift_count=0,
                negative_drift_count=0, zero_drift_count=0,
                max_positive_drift=0, max_negative_drift=0,
                drift_by_outcome={}, drift_by_difficulty={},
                results=[], insights=["バッファ空 — 再評価不可"],
            )

        if prioritized:
            batch = replay.sample_prioritized(min(sample_size, replay.size * 3))
        else:
            batch = replay.sample(min(sample_size, replay.size))

        # 重複を task_id で除去（prioritized は重複あり）
        seen = set()
        unique = []
        for exp in batch:
            if exp.task_id not in seen:
                seen.add(exp.task_id)
                unique.append(exp)

        return self.evaluate_batch(unique)

    def _explain_drift(self, exp: Experience, new_score: float, drift: float) -> str:
        """ドリフトの理由を自然言語で説明"""
        parts = []
        if abs(drift) < 0.01:
            return "スコア変化なし"

        direction = "上昇" if drift > 0 else "低下"
        parts.append(f"スコア{direction} ({exp.score:.2f} → {new_score:.2f})")

        if exp.error_count > 0 and exp.tool_count > 0:
            er = exp.error_count / exp.tool_count
            if er > 0.3:
                parts.append(f"エラー率高({er:.0%})")

        if exp.tool_count > 30:
            parts.append("ツール過多")
        elif exp.tool_count <= 2:
            parts.append("ツール少")

        if exp.difficulty == "abstract" and exp.outcome == "success":
            parts.append("高難度成功ボーナス")

        return "; ".join(parts)

    def _extract_insights(
        self,
        results: List[ReEvalResult],
        outcome_avg: Dict[str, float],
        diff_avg: Dict[str, float],
        total_avg: float,
    ) -> List[str]:
        """パターンからインサイトを抽出"""
        insights = []

        if abs(total_avg) < 0.01:
            insights.append("全体的にスコアリング基準は安定 — 大きな乖離なし")
        elif total_avg > 0.05:
            insights.append(f"新基準で全体的にスコア向上 (+{total_avg:.3f}) — 基準が緩和傾向")
        elif total_avg < -0.05:
            insights.append(f"新基準で全体的にスコア低下 ({total_avg:.3f}) — 基準が厳格化傾向")

        # Outcome 別
        for outcome, avg in outcome_avg.items():
            if avg > 0.1:
                insights.append(f"{outcome} タスクのスコアが新基準で大幅向上 (+{avg:.3f})")
            elif avg < -0.1:
                insights.append(f"{outcome} タスクのスコアが新基準で大幅低下 ({avg:.3f})")

        # Difficulty 別
        for diff, avg in diff_avg.items():
            if avg > 0.08:
                insights.append(f"難易度 {diff} のスコアが向上 (+{avg:.3f}) — この難易度は適切")
            elif avg < -0.08:
                insights.append(f"難易度 {diff} のスコアが低下 ({avg:.3f}) — 調整を検討")

        if not insights:
            insights.append("特筆すべきパターンなし")

        return insights
