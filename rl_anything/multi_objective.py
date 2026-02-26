#!/usr/bin/env python3
"""
Multi-Objective Optimizer
=========================
複数の競合するメトリクス（精度 vs 速度, 探索 vs 活用 等）を
パレートフロント上で同時最適化する。

主要概念:
  - Objective: 最適化対象の名前付きメトリクス (方向: maximize / minimize)
  - Solution:  複数 Objective の値を持つ1つの解
  - ParetoFront: 支配されていない解の集合 (非劣解)
  - Scalarization: 重み付き線形結合で単一スコアに変換

使い方::

    mo = MultiObjectiveOptimizer()
    mo.add_objective("accuracy", direction="maximize", weight=0.6)
    mo.add_objective("speed",    direction="maximize", weight=0.4)

    mo.record_solution(cycle=1, values={"accuracy": 0.85, "speed": 0.9})
    mo.record_solution(cycle=2, values={"accuracy": 0.92, "speed": 0.7})

    front = mo.get_pareto_front()
    scalar = mo.scalarize({"accuracy": 0.90, "speed": 0.80})
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

_log = logging.getLogger("rl_anything.multi_objective")

# ═══════════════════════════════════════════════════════════
# データ構造
# ═══════════════════════════════════════════════════════════

@dataclass
class Objective:
    """最適化対象のメトリクス定義"""
    name: str
    direction: Literal["maximize", "minimize"] = "maximize"
    weight: float = 1.0
    # 正規化用の観測範囲
    observed_min: float = float("inf")
    observed_max: float = float("-inf")

    def normalize(self, value: float) -> float:
        """[0, 1] に正規化 (direction 考慮済み: 大きい方が良い)"""
        span = self.observed_max - self.observed_min
        if span <= 0:
            return 0.5
        normed = (value - self.observed_min) / span
        if self.direction == "minimize":
            normed = 1.0 - normed
        return max(0.0, min(1.0, normed))


@dataclass
class Solution:
    """1つの解（あるサイクルでの各メトリクス値）"""
    cycle: int
    values: Dict[str, float]
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    scalarized: float = 0.0  # 後から計算
    is_pareto: bool = False  # パレートフロントに入っているか


# ═══════════════════════════════════════════════════════════
# Multi-Objective Optimizer
# ═══════════════════════════════════════════════════════════

class MultiObjectiveOptimizer:
    """
    パレートフロント追跡と重み付きスカラー化による多目的最適化。
    """

    MAX_SOLUTIONS = 500  # 保持する解の上限

    # デフォルト Objectives — RLAnything に適したメトリクス
    DEFAULT_OBJECTIVES = [
        Objective(name="score", direction="maximize", weight=0.35),
        Objective(name="success_rate", direction="maximize", weight=0.25),
        Objective(name="efficiency", direction="maximize", weight=0.20),
        Objective(name="exploration", direction="maximize", weight=0.20),
    ]

    def __init__(
        self,
        objectives: Optional[List[Objective]] = None,
        persist_path: Optional[Path] = None,
    ):
        self._objectives: Dict[str, Objective] = {}
        self._solutions: List[Solution] = []
        self._persist_path = persist_path

        # 初期 Objectives 登録
        for obj in (objectives or self.DEFAULT_OBJECTIVES):
            self._objectives[obj.name] = obj

        # 永続化から復元
        self._restore()

    # ───────────────── Objective 管理 ─────────────────

    def add_objective(
        self,
        name: str,
        direction: str = "maximize",
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Objective を追加 / 更新"""
        obj = Objective(name=name, direction=direction, weight=weight)
        self._objectives[name] = obj
        return {"added": name, "direction": direction, "weight": weight}

    def remove_objective(self, name: str) -> bool:
        """Objective を削除"""
        if name in self._objectives:
            del self._objectives[name]
            return True
        return False

    def get_objectives(self) -> Dict[str, Dict[str, Any]]:
        """登録済み Objective 一覧"""
        return {
            name: {
                "direction": obj.direction,
                "weight": obj.weight,
                "observed_min": obj.observed_min if obj.observed_min != float("inf") else None,
                "observed_max": obj.observed_max if obj.observed_max != float("-inf") else None,
            }
            for name, obj in self._objectives.items()
        }

    # ───────────────── Solution 記録 ─────────────────

    def record_solution(
        self,
        cycle: int,
        values: Dict[str, float],
    ) -> Solution:
        """
        解を記録。
        - 観測範囲を更新
        - スカラー化スコアを計算
        - パレートフロントを再計算
        """
        # 観測範囲を更新
        for name, val in values.items():
            if name in self._objectives:
                obj = self._objectives[name]
                obj.observed_min = min(obj.observed_min, val)
                obj.observed_max = max(obj.observed_max, val)

        # スカラー化
        scalar = self.scalarize(values)

        sol = Solution(
            cycle=cycle,
            values=dict(values),
            scalarized=scalar,
        )
        self._solutions.append(sol)

        # 上限超え → 古い非パレート解を捨てる
        if len(self._solutions) > self.MAX_SOLUTIONS:
            self._prune()

        # パレートフロント再計算
        self._update_pareto()

        self._persist()
        return sol

    def scalarize(self, values: Dict[str, float]) -> float:
        """
        重み付き線形結合でスカラー化。
        各値は Objective の observed 範囲で正規化してから加重和。
        """
        total_weight = sum(
            obj.weight for obj in self._objectives.values()
            if obj.name in values
        )
        if total_weight <= 0:
            return 0.0

        weighted_sum = 0.0
        for name, val in values.items():
            obj = self._objectives.get(name)
            if obj is None:
                continue
            normed = obj.normalize(val)
            weighted_sum += normed * obj.weight

        return round(weighted_sum / total_weight, 6)

    # ───────────────── パレート計算 ─────────────────

    def _dominates(self, a: Solution, b: Solution) -> bool:
        """
        解 a が b を支配するか (全 Objective で a >= b かつ少なくとも1つで a > b)。
        direction に従い正規化されたスコアで比較。
        """
        at_least_one_better = False
        for name, obj in self._objectives.items():
            va = obj.normalize(a.values.get(name, 0))
            vb = obj.normalize(b.values.get(name, 0))
            if va < vb:
                return False
            if va > vb:
                at_least_one_better = True
        return at_least_one_better

    def _update_pareto(self) -> None:
        """全解についてパレート支配を判定"""
        n = len(self._solutions)
        for i in range(n):
            self._solutions[i].is_pareto = True

        for i in range(n):
            if not self._solutions[i].is_pareto:
                continue
            for j in range(n):
                if i == j:
                    continue
                if not self._solutions[j].is_pareto:
                    continue
                if self._dominates(self._solutions[j], self._solutions[i]):
                    self._solutions[i].is_pareto = False
                    break

    def _prune(self) -> None:
        """MAX_SOLUTIONS を超えた場合、古い非パレート解を削除"""
        self._update_pareto()
        # パレート解は残す、非パレート解を古い順に捨てる
        pareto = [s for s in self._solutions if s.is_pareto]
        non_pareto = [s for s in self._solutions if not s.is_pareto]
        keep = max(0, self.MAX_SOLUTIONS - len(pareto))
        self._solutions = pareto + non_pareto[-keep:]

    def get_pareto_front(self) -> List[Dict[str, Any]]:
        """現在のパレートフロント (非劣解集合) を返す"""
        self._update_pareto()
        return [
            {
                "cycle": s.cycle,
                "values": s.values,
                "scalarized": s.scalarized,
                "ts": s.ts,
            }
            for s in self._solutions
            if s.is_pareto
        ]

    def get_best_scalarized(self) -> Optional[Dict[str, Any]]:
        """スカラー化スコアが最高の解を返す"""
        if not self._solutions:
            return None
        best = max(self._solutions, key=lambda s: s.scalarized)
        return {
            "cycle": best.cycle,
            "values": best.values,
            "scalarized": best.scalarized,
            "ts": best.ts,
            "is_pareto": best.is_pareto,
        }

    # ───────────────── 分析 ─────────────────

    def get_trade_off_analysis(self) -> Dict[str, Any]:
        """
        Objective 間のトレードオフを分析。
        相関行列 (ピアソン) + 各 Objective のトレンド。
        """
        if len(self._solutions) < 3:
            return {"status": "insufficient_data", "min_required": 3}

        names = list(self._objectives.keys())
        n = len(self._solutions)

        # 各 Objective の系列
        series: Dict[str, List[float]] = {name: [] for name in names}
        for sol in self._solutions:
            for name in names:
                series[name].append(sol.values.get(name, 0))

        # ピアソン相関行列
        correlations: Dict[str, Dict[str, float]] = {}
        for a_name in names:
            correlations[a_name] = {}
            for b_name in names:
                correlations[a_name][b_name] = self._pearson(series[a_name], series[b_name])

        # 各 Objective のトレンド (最新 1/3 vs 最初 1/3)
        trends: Dict[str, str] = {}
        split = max(1, n // 3)
        for name in names:
            early_avg = sum(series[name][:split]) / max(1, split)
            late_avg = sum(series[name][-split:]) / max(1, split)
            diff = late_avg - early_avg
            if abs(diff) < 0.01:
                trends[name] = "stable"
            elif diff > 0:
                trends[name] = "improving" if self._objectives[name].direction == "maximize" else "worsening"
            else:
                trends[name] = "worsening" if self._objectives[name].direction == "maximize" else "improving"

        # 競合ペア検出 (負の相関)
        conflicts = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                corr = correlations[a][b]
                if corr < -0.3:
                    conflicts.append({
                        "objectives": [a, b],
                        "correlation": round(corr, 4),
                        "severity": "high" if corr < -0.6 else "moderate",
                    })

        return {
            "correlations": correlations,
            "trends": trends,
            "conflicts": conflicts,
            "solution_count": n,
            "pareto_size": sum(1 for s in self._solutions if s.is_pareto),
        }

    @staticmethod
    def _pearson(x: List[float], y: List[float]) -> float:
        """ピアソン相関係数"""
        n = len(x)
        if n < 2:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        sx = math.sqrt(max(0, sum((xi - mx) ** 2 for xi in x) / n))
        sy = math.sqrt(max(0, sum((yi - my) ** 2 for yi in y) / n))
        if sx == 0 or sy == 0:
            return 0.0
        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
        return round(cov / (sx * sy), 4)

    # ───────────────── 推奨 ─────────────────

    def recommend_weights(self) -> Dict[str, float]:
        """
        現在の trade-off 分析に基づいて重みを推奨。
        改善余地の大きい Objective に重みを寄せる。
        """
        if len(self._solutions) < 5:
            return {name: obj.weight for name, obj in self._objectives.items()}

        # 各 Objective の改善度合い (最新 5 件 / 全体 の正規化平均)
        recent = self._solutions[-5:]
        improvement_room: Dict[str, float] = {}
        for name, obj in self._objectives.items():
            recent_avg = sum(obj.normalize(s.values.get(name, 0)) for s in recent) / len(recent)
            # 改善余地 = 1 - recent_avg (正規化値なので 1.0 が最良)
            improvement_room[name] = max(0, 1.0 - recent_avg)

        total_room = sum(improvement_room.values())
        if total_room <= 0:
            return {name: obj.weight for name, obj in self._objectives.items()}

        recommended = {}
        for name in self._objectives:
            # 改善余地に比例 + 現在の重みのブレンド (50:50)
            room_weight = improvement_room[name] / total_room
            current = self._objectives[name].weight
            recommended[name] = round(0.5 * current + 0.5 * room_weight, 4)
        return recommended

    # ───────────────── 統計 ─────────────────

    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        self._update_pareto()
        pareto_count = sum(1 for s in self._solutions if s.is_pareto)
        return {
            "total_solutions": len(self._solutions),
            "pareto_size": pareto_count,
            "objectives": list(self._objectives.keys()),
            "objective_count": len(self._objectives),
            "best_scalarized": self.get_best_scalarized(),
            "recommended_weights": self.recommend_weights() if len(self._solutions) >= 5 else None,
        }

    # ───────────────── 永続化 ─────────────────

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "objectives": {
                    name: {
                        "direction": obj.direction,
                        "weight": obj.weight,
                        "observed_min": obj.observed_min if obj.observed_min != float("inf") else None,
                        "observed_max": obj.observed_max if obj.observed_max != float("-inf") else None,
                    }
                    for name, obj in self._objectives.items()
                },
                "solutions": [
                    {"cycle": s.cycle, "values": s.values, "ts": s.ts, "scalarized": s.scalarized}
                    for s in self._solutions[-self.MAX_SOLUTIONS:]
                ],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("multi-objective persist failed: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            # Objective の観測範囲を復元
            for name, odata in data.get("objectives", {}).items():
                if name in self._objectives:
                    obj = self._objectives[name]
                    if odata.get("observed_min") is not None:
                        obj.observed_min = odata["observed_min"]
                    if odata.get("observed_max") is not None:
                        obj.observed_max = odata["observed_max"]
                    obj.weight = odata.get("weight", obj.weight)
            # Solution を復元
            for sdata in data.get("solutions", []):
                sol = Solution(
                    cycle=sdata["cycle"],
                    values=sdata["values"],
                    ts=sdata.get("ts", ""),
                    scalarized=sdata.get("scalarized", 0),
                )
                self._solutions.append(sol)
            self._update_pareto()
        except Exception as e:
            _log.warning("multi-objective restore failed: %s", e)
