#!/usr/bin/env python3
"""
Model-Based Planner — 世界モデル + 先読み計画
================================================
状態遷移(transition)と報酬(reward)を学習し、
実際のインタラクションなしに"将来の結果"をシミュレーション。
Monte-Carlo Tree Search 的な先読みで最適行動を計画する。

Princeton RL-Anything Round 10 Module 1.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════
# 定数
# ═══════════════════════════════════════════════════════
ACTIONS = ["level_down", "stay", "level_up"]
MAX_TRANSITIONS = 5000
PLANNING_DEPTH = 3
PLANNING_SIMULATIONS = 50
TRANSITION_LR = 0.1
DISCOUNT = 0.95
UCB_C = 1.41  # UCB exploration constant


# ═══════════════════════════════════════════════════════
# データクラス
# ═══════════════════════════════════════════════════════
@dataclass
class Transition:
    """状態遷移レコード"""
    state: str
    action: str
    next_state: str
    reward: float
    cycle: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorldModel:
    """学習済み世界モデル (遷移確率 + 報酬予測)"""
    transition_counts: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    reward_estimates: Dict[str, Dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(float)))
    reward_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))

    def predict_next_state(self, state: str, action: str) -> str:
        """遷移確率に基づいて次状態を予測"""
        counts = self.transition_counts.get(state, {}).get(action, {})
        if not counts:
            return state  # 未知 → 現状維持
        total = sum(counts.values())
        r = random.random() * total
        cumulative = 0
        for next_s, c in counts.items():
            cumulative += c
            if cumulative >= r:
                return next_s
        return state

    def predict_reward(self, state: str, action: str) -> float:
        """期待報酬を予測"""
        return self.reward_estimates.get(state, {}).get(action, 0.5)

    def update(self, transition: Transition) -> None:
        """遷移から世界モデルを更新"""
        s, a, ns, r = transition.state, transition.action, transition.next_state, transition.reward
        self.transition_counts[s][a][ns] += 1
        # 報酬の指数移動平均
        n = self.reward_counts[s][a] + 1
        self.reward_counts[s][a] = n
        old_r = self.reward_estimates[s][a]
        self.reward_estimates[s][a] = old_r + TRANSITION_LR * (r - old_r)

    def accuracy(self) -> float:
        """モデル精度の推定 (知識量ベース)"""
        total = sum(
            sum(sum(v.values()) for v in actions.values())
            for actions in self.transition_counts.values()
        )
        if total == 0:
            return 0.0
        # 対数スケーリング: 多くのデータ → 高精度
        return min(1.0, math.log(1 + total) / math.log(1 + 1000))


@dataclass
class PlanResult:
    """計画結果"""
    best_action: str
    expected_value: float
    action_values: Dict[str, float]
    simulations: int
    depth: int
    model_accuracy: float
    confidence: float  # action間のマージン

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanningStats:
    """計画エンジン全体統計"""
    total_plans: int = 0
    total_transitions: int = 0
    unique_states: int = 0
    model_accuracy: float = 0.0
    avg_plan_value: float = 0.0
    action_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_distribution"] = dict(d["action_distribution"])
        return d


# ═══════════════════════════════════════════════════════
# メインクラス
# ═══════════════════════════════════════════════════════
class ModelBasedPlanner:
    """
    世界モデルを学習し、先読み計画で最適行動を推奨する。
    - 遷移 (state, action) → next_state を統計的に学習
    - 報酬 (state, action) → reward を EMA で追跡
    - Monte-Carlo rollout で先読み計画
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        planning_depth: int = PLANNING_DEPTH,
        simulations: int = PLANNING_SIMULATIONS,
    ):
        self._persist_path = persist_path
        self._depth = planning_depth
        self._simulations = simulations

        self._world = WorldModel()
        self._transitions: List[Transition] = []
        self._plans: List[PlanResult] = []
        self._total_plans = 0
        self._plan_value_sum = 0.0

        self._restore()

    # ═══════════════════════════════════════════════════════
    # 状態エンコーディング
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def encode_state(difficulty: str, success_rate: float, cycle: int) -> str:
        """状態を離散化ハッシュに変換"""
        sr_bucket = round(success_rate * 10) / 10  # 0.1刻み
        cycle_bucket = min(cycle // 10, 20)  # 10サイクル刻み、上限20
        raw = f"{difficulty}|{sr_bucket:.1f}|{cycle_bucket}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    # ═══════════════════════════════════════════════════════
    # 遷移記録
    # ═══════════════════════════════════════════════════════
    def record_transition(
        self,
        state: str,
        action: str,
        next_state: str,
        reward: float,
        cycle: int,
    ) -> Transition:
        """実際の遷移を記録し世界モデルを更新"""
        t = Transition(state=state, action=action, next_state=next_state, reward=reward, cycle=cycle)
        self._transitions.append(t)
        if len(self._transitions) > MAX_TRANSITIONS:
            self._transitions = self._transitions[-MAX_TRANSITIONS:]
        self._world.update(t)
        self._persist()
        return t

    # ═══════════════════════════════════════════════════════
    # 計画 (Monte-Carlo Rollout)
    # ═══════════════════════════════════════════════════════
    def plan(self, current_state: str) -> PlanResult:
        """
        Monte-Carlo rollout で各アクションの期待値を推定し、
        最適アクションを返す。
        """
        action_values: Dict[str, float] = {}
        action_counts: Dict[str, int] = defaultdict(int)
        total_value: Dict[str, float] = defaultdict(float)

        for _ in range(self._simulations):
            # UCB1 でアクション選択
            for a in ACTIONS:
                if action_counts[a] == 0:
                    chosen = a
                    break
            else:
                total_n = sum(action_counts.values())
                chosen = max(
                    ACTIONS,
                    key=lambda a: (total_value[a] / max(1, action_counts[a]))
                    + UCB_C * math.sqrt(math.log(total_n) / max(1, action_counts[a]))
                )

            # Rollout
            value = self._rollout(current_state, chosen, self._depth)
            total_value[chosen] += value
            action_counts[chosen] += 1

        # 各アクションの平均値
        for a in ACTIONS:
            if action_counts[a] > 0:
                action_values[a] = round(total_value[a] / action_counts[a], 4)
            else:
                action_values[a] = 0.0

        best_action = max(action_values, key=lambda a: action_values[a])
        best_val = action_values[best_action]

        # 信頼度 = ベストと2位の差
        sorted_vals = sorted(action_values.values(), reverse=True)
        margin = sorted_vals[0] - sorted_vals[1] if len(sorted_vals) >= 2 else sorted_vals[0]
        confidence = min(1.0, margin / max(0.01, best_val))

        result = PlanResult(
            best_action=best_action,
            expected_value=round(best_val, 4),
            action_values=action_values,
            simulations=self._simulations,
            depth=self._depth,
            model_accuracy=round(self._world.accuracy(), 4),
            confidence=round(confidence, 4),
        )

        self._plans.append(result)
        self._total_plans += 1
        self._plan_value_sum += best_val
        self._persist()
        return result

    def _rollout(self, state: str, first_action: str, depth: int) -> float:
        """
        first_action から始めて depth ステップ先までの累積報酬を推定。
        """
        total = 0.0
        discount = 1.0
        s = state
        a = first_action

        for d in range(depth):
            r = self._world.predict_reward(s, a)
            total += discount * r
            discount *= DISCOUNT

            s = self._world.predict_next_state(s, a)
            # 次ステップはランダムポリシー（探索）
            a = random.choice(ACTIONS)

        return total

    # ═══════════════════════════════════════════════════════
    # ユーティリティ
    # ═══════════════════════════════════════════════════════
    def get_transition_count(self) -> int:
        """記録された遷移数"""
        return len(self._transitions)

    def get_recent_transitions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """直近の遷移"""
        return [t.to_dict() for t in self._transitions[-limit:]]

    def get_recent_plans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """直近の計画結果"""
        return [p.to_dict() for p in self._plans[-limit:]]

    def get_model_info(self) -> Dict[str, Any]:
        """世界モデルの情報"""
        unique_states = set()
        for s in self._world.transition_counts:
            unique_states.add(s)
            for a in self._world.transition_counts[s]:
                for ns in self._world.transition_counts[s][a]:
                    unique_states.add(ns)

        total_transitions = sum(
            sum(sum(v.values()) for v in actions.values())
            for actions in self._world.transition_counts.values()
        )

        return {
            "unique_states": len(unique_states),
            "total_observed_transitions": total_transitions,
            "model_accuracy": round(self._world.accuracy(), 4),
            "transition_pairs": sum(
                len(actions) for actions in self._world.transition_counts.values()
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """全体統計"""
        model_info = self.get_model_info()
        action_dist: Dict[str, int] = defaultdict(int)
        for p in self._plans:
            action_dist[p.best_action] += 1

        return {
            "total_plans": self._total_plans,
            "total_transitions": len(self._transitions),
            "unique_states": model_info["unique_states"],
            "model_accuracy": model_info["model_accuracy"],
            "avg_plan_value": round(self._plan_value_sum / max(1, self._total_plans), 4),
            "action_distribution": dict(action_dist),
            "planning_depth": self._depth,
            "simulations_per_plan": self._simulations,
        }

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            # transition_counts を直列化可能な形に変換
            tc = {}
            for s, actions in self._world.transition_counts.items():
                tc[s] = {}
                for a, nexts in actions.items():
                    tc[s][a] = dict(nexts)

            re = {}
            for s, actions in self._world.reward_estimates.items():
                re[s] = dict(actions)

            rc = {}
            for s, actions in self._world.reward_counts.items():
                rc[s] = dict(actions)

            data = {
                "transitions": [t.to_dict() for t in self._transitions[-MAX_TRANSITIONS:]],
                "transition_counts": tc,
                "reward_estimates": re,
                "reward_counts": rc,
                "total_plans": self._total_plans,
                "plan_value_sum": self._plan_value_sum,
                "plans": [p.to_dict() for p in self._plans[-50:]],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))

            # Transitions
            for t in data.get("transitions", []):
                self._transitions.append(Transition(**t))

            # World model
            tc = data.get("transition_counts", {})
            for s, actions in tc.items():
                for a, nexts in actions.items():
                    for ns, cnt in nexts.items():
                        self._world.transition_counts[s][a][ns] = cnt

            re = data.get("reward_estimates", {})
            for s, actions in re.items():
                for a, val in actions.items():
                    self._world.reward_estimates[s][a] = val

            rc = data.get("reward_counts", {})
            for s, actions in rc.items():
                for a, cnt in actions.items():
                    self._world.reward_counts[s][a] = cnt

            self._total_plans = data.get("total_plans", 0)
            self._plan_value_sum = data.get("plan_value_sum", 0.0)

            # Plans
            for p in data.get("plans", []):
                self._plans.append(PlanResult(**p))
        except Exception:
            pass
