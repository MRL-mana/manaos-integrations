#!/usr/bin/env python3
"""
CausalReasoning — 因果推論による報酬帰属 & 反事実分析
====================================================
Round 11 モジュール (3/3)

ツール使用とスコアの因果関係を推定し、アクションの効果を
因果的に分離する。介入効果の推定と反事実シミュレーションを提供。

主な機能:
  - ツール→スコアの因果インパクト推定
  - 反事実分析（もし〇〇しなかったら）
  - 介入効果推定（do-calculus 簡易版）
  - 因果グラフ構築（ツール依存関係）
  - 寄与帰属（各アクションの報酬への寄与）
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── 定数 ──

MAX_OBSERVATIONS = 5000
MIN_SAMPLES_FOR_CAUSAL = 3
SMOOTHING_ALPHA = 0.1  # 指数移動平均の平滑化係数
ATTRIBUTION_DECAY = 0.95  # 寄与帰属の時間減衰


# ── データ型 ──

@dataclass
class CausalObservation:
    """1回の因果観測"""
    task_id: str
    tools_used: List[str]
    score: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "tools_used": self.tools_used,
            "score": self.score,
            "timestamp": self.timestamp,
        }


@dataclass
class CausalEffect:
    """因果効果の推定結果"""
    tool: str
    ate: float              # Average Treatment Effect
    confidence: float
    n_treatment: int        # ツールを使ったタスク数
    n_control: int          # ツールを使わなかったタスク数
    treatment_mean: float
    control_mean: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CounterfactualResult:
    """反事実分析の結果"""
    scenario: str
    actual_score: float
    counterfactual_score: float
    effect: float           # actual - counterfactual
    tools_removed: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Attribution:
    """アクション寄与帰属"""
    tool: str
    attribution_score: float    # 報酬への寄与度
    frequency: float            # 使用頻度
    avg_score_with: float       # 使用時の平均スコア
    avg_score_without: float    # 未使用時の平均スコア

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── メインクラス ──

class CausalReasoning:
    """因果推論エンジン"""

    def __init__(self, *, persist_path: Optional[Path] = None,
                 config: Optional[Dict] = None):
        self._observations: List[CausalObservation] = []

        # ツール別統計（指数移動平均）
        self._tool_ema: Dict[str, float] = defaultdict(float)
        self._tool_count: Dict[str, int] = defaultdict(int)

        # 因果グラフ（ツール共起頻度）
        self._cooccurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        self._persist = persist_path
        cfg = config or {}
        self._smoothing = cfg.get("causal_smoothing", SMOOTHING_ALPHA)
        self._decay = cfg.get("causal_decay", ATTRIBUTION_DECAY)

        self._restore()

    # ── 観測記録 ──

    def record_observation(self, task_id: str, tools_used: List[str],
                           score: float, timestamp: Optional[float] = None) -> CausalObservation:
        """因果観測を記録"""
        ts = timestamp or time.time()
        obs = CausalObservation(task_id, tools_used, score, ts)
        self._observations.append(obs)

        # EMA更新
        for tool in tools_used:
            old = self._tool_ema.get(tool, score)
            self._tool_ema[tool] = old + self._smoothing * (score - old)
            self._tool_count[tool] = self._tool_count.get(tool, 0) + 1

        # 共起更新
        for i, t1 in enumerate(tools_used):
            for t2 in tools_used[i + 1:]:
                self._cooccurrence[t1][t2] += 1
                self._cooccurrence[t2][t1] += 1

        # 容量制限
        if len(self._observations) > MAX_OBSERVATIONS:
            self._observations = self._observations[-MAX_OBSERVATIONS:]

        self._persist_state()
        return obs

    # ── 因果効果推定（ATE） ──

    def estimate_causal_effect(self, tool: str) -> CausalEffect:
        """
        指定ツールの Average Treatment Effect を推定。
        treatment = ツールを使ったタスク, control = 使わなかったタスク
        """
        treatment_scores = []
        control_scores = []

        for obs in self._observations:
            if tool in obs.tools_used:
                treatment_scores.append(obs.score)
            else:
                control_scores.append(obs.score)

        n_t = len(treatment_scores)
        n_c = len(control_scores)

        if n_t == 0 or n_c == 0:
            return CausalEffect(
                tool=tool, ate=0.0, confidence=0.0,
                n_treatment=n_t, n_control=n_c,
                treatment_mean=sum(treatment_scores) / max(1, n_t),
                control_mean=sum(control_scores) / max(1, n_c),
            )

        t_mean = sum(treatment_scores) / n_t
        c_mean = sum(control_scores) / n_c
        ate = t_mean - c_mean

        # 信頼度: サンプル数ベース
        confidence = min(1.0, min(n_t, n_c) / 10.0)

        return CausalEffect(
            tool=tool, ate=round(ate, 4), confidence=round(confidence, 3),
            n_treatment=n_t, n_control=n_c,
            treatment_mean=round(t_mean, 4), control_mean=round(c_mean, 4),
        )

    # ── 反事実分析 ──

    def counterfactual(self, task_id: str,
                       remove_tools: List[str]) -> CounterfactualResult:
        """
        反事実分析: もし指定ツールを使わなかったら？
        """
        # 対象タスクを探す
        target = None
        for obs in reversed(self._observations):
            if obs.task_id == task_id:
                target = obs
                break

        if target is None:
            return CounterfactualResult(
                scenario=f"remove {remove_tools}",
                actual_score=0.0, counterfactual_score=0.0,
                effect=0.0, tools_removed=remove_tools, confidence=0.0,
            )

        actual = target.score

        # 反事実スコア推定: 除外ツールの因果効果を差し引く
        cf_score = actual
        for tool in remove_tools:
            if tool in target.tools_used:
                effect = self.estimate_causal_effect(tool)
                cf_score -= effect.ate

        cf_score = max(0.0, min(1.0, cf_score))
        confidence = min(1.0, len(self._observations) / 20.0)

        return CounterfactualResult(
            scenario=f"remove {remove_tools} from {task_id}",
            actual_score=round(actual, 4),
            counterfactual_score=round(cf_score, 4),
            effect=round(actual - cf_score, 4),
            tools_removed=remove_tools,
            confidence=round(confidence, 3),
        )

    # ── 寄与帰属 ──

    def get_attributions(self, top_k: int = 10) -> List[Attribution]:
        """全ツールの報酬寄与帰属（Shapley値的）"""
        if not self._observations:
            return []

        all_tools = set()
        for obs in self._observations:
            all_tools.update(obs.tools_used)

        total_obs = len(self._observations)
        attributions = []

        for tool in all_tools:
            effect = self.estimate_causal_effect(tool)
            freq = self._tool_count.get(tool, 0) / total_obs

            attributions.append(Attribution(
                tool=tool,
                attribution_score=round(effect.ate * freq, 4),
                frequency=round(freq, 4),
                avg_score_with=effect.treatment_mean,
                avg_score_without=effect.control_mean,
            ))

        # 寄与度順にソート
        attributions.sort(key=lambda a: abs(a.attribution_score), reverse=True)
        return attributions[:top_k]

    # ── 因果グラフ ──

    def get_causal_graph(self) -> Dict[str, Any]:
        """ツール間の依存関係グラフ"""
        nodes = set()
        for obs in self._observations:
            nodes.update(obs.tools_used)

        edges = []
        for t1, neighbors in self._cooccurrence.items():
            for t2, count in neighbors.items():
                if t1 < t2:  # 重複排除
                    edges.append({
                        "source": t1, "target": t2,
                        "weight": count,
                    })

        return {
            "nodes": sorted(nodes),
            "edges": sorted(edges, key=lambda e: e["weight"], reverse=True),
            "total_tools": len(nodes),
            "total_edges": len(edges),
        }

    # ── 介入効果 ──

    def intervention_effect(self, tool: str,
                            context_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        do(tool) の効果推定。context_tools が指定されている場合、
        そのコンテキスト下での条件付き効果を推定。
        """
        if context_tools is None:
            effect = self.estimate_causal_effect(tool)
            return {
                "tool": tool, "effect": effect.ate,
                "confidence": effect.confidence,
                "type": "marginal",
            }

        # コンテキスト条件付き推定
        ctx_set = set(context_tools)
        treatment_scores = []
        control_scores = []

        for obs in self._observations:
            tools_set = set(obs.tools_used)
            if ctx_set.issubset(tools_set):
                if tool in tools_set:
                    treatment_scores.append(obs.score)
                else:
                    control_scores.append(obs.score)

        n_t = len(treatment_scores)
        n_c = len(control_scores)

        if n_t == 0 or n_c == 0:
            return {
                "tool": tool, "effect": 0.0, "confidence": 0.0,
                "type": "conditional", "context": context_tools,
                "n_treatment": n_t, "n_control": n_c,
            }

        t_mean = sum(treatment_scores) / n_t
        c_mean = sum(control_scores) / n_c

        return {
            "tool": tool, "effect": round(t_mean - c_mean, 4),
            "confidence": round(min(1.0, min(n_t, n_c) / 5.0), 3),
            "type": "conditional", "context": context_tools,
            "n_treatment": n_t, "n_control": n_c,
        }

    # ── 統計 ──

    def get_stats(self) -> Dict[str, Any]:
        """全体統計"""
        return {
            "total_observations": len(self._observations),
            "unique_tools": len(self._tool_count),
            "total_tool_uses": sum(self._tool_count.values()),
            "cooccurrence_pairs": sum(
                len(v) for v in self._cooccurrence.values()) // 2,
            "tool_ema": dict(self._tool_ema),
        }

    # ── 永続化 ──

    def _persist_state(self) -> None:
        if not self._persist:
            return
        try:
            data = {
                "observations": [o.to_dict() for o in self._observations[-MAX_OBSERVATIONS:]],
                "tool_ema": dict(self._tool_ema),
                "tool_count": dict(self._tool_count),
                "cooccurrence": {
                    k: dict(v) for k, v in self._cooccurrence.items()
                },
            }
            self._persist.parent.mkdir(parents=True, exist_ok=True)
            self._persist.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _restore(self) -> None:
        if not self._persist or not self._persist.exists():
            return
        try:
            data = json.loads(self._persist.read_text(encoding="utf-8"))
            for od in data.get("observations", []):
                self._observations.append(CausalObservation(**od))
            self._tool_ema = defaultdict(float, data.get("tool_ema", {}))
            self._tool_count = defaultdict(int, data.get("tool_count", {}))
            raw_co = data.get("cooccurrence", {})
            for k, v in raw_co.items():
                self._cooccurrence[k] = defaultdict(int, v)
        except Exception:
            pass
