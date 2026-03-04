#!/usr/bin/env python3
"""
Ensemble Policy
===============
複数のポリシー（方策）を組み合わせてロバストな意思決定を行う。

アンサンブル手法:
  1. **Majority Vote** — 多数決。各ポリシーの推奨アクションの投票数で決定。
  2. **Weighted Average** — 各ポリシーの確率分布を性能加重で平均。
  3. **Boltzmann Mix** — 各ポリシーの信頼度をBoltzmann温度で混合。
  4. **Best-of-N** — 直近パフォーマンスが最良のポリシーをそのまま採用。

主要概念:
  - PolicyMember: アンサンブル中の1つのポリシーインスタンス
  - EnsembleDecision: 複数ポリシーの統合結果
  - Diversity Metric: ポリシー間の多様性指標

使い方::

    ep = EnsemblePolicy(n_members=3)
    decision = ep.decide(state=[0.7, 0.8, 0.5])
    # → EnsembleDecision with action, confidence, agreement
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

_log = logging.getLogger("rl_anything.ensemble_policy")

# ═══════════════════════════════════════════════════════════
# 定数
# ═══════════════════════════════════════════════════════════

ACTIONS = ["level_down", "stay", "level_up"]
STATE_DIM = 3  # success_rate, avg_score, difficulty_encoded
ACTION_DIM = 3

# ═══════════════════════════════════════════════════════════
# データ構造
# ═══════════════════════════════════════════════════════════

@dataclass
class PolicyMember:
    """アンサンブルの1メンバー"""
    member_id: int
    # 線形ポリシーパラメータ
    theta: List[List[float]]      # STATE_DIM x ACTION_DIM
    bias: List[float]             # ACTION_DIM
    temperature: float = 1.0
    # パフォーマンストラッキング
    total_reward: float = 0.0
    decision_count: int = 0
    correct_count: int = 0        # 「正解」= アンサンブル合意と一致

    @property
    def avg_reward(self) -> float:
        return self.total_reward / max(1, self.decision_count)

    @property
    def accuracy(self) -> float:
        return self.correct_count / max(1, self.decision_count)


@dataclass
class EnsembleDecision:
    """アンサンブルの統合決定"""
    action: str
    # 各アクションの統合確率
    probabilities: Dict[str, float]
    # 合意度 (0-1, 1=全員一致)
    agreement: float
    # 信頼度 (確率の集中度)
    confidence: float
    # 各メンバーの推奨
    member_votes: List[Dict[str, Any]]
    # 使用した集約手法
    method: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "agreement": round(self.agreement, 4),
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "member_votes": self.member_votes,
        }


# ═══════════════════════════════════════════════════════════
# Ensemble Policy
# ═══════════════════════════════════════════════════════════

class EnsemblePolicy:
    """
    複数ポリシーを組み合わせた意思決定。
    各メンバーはランダムに初期化された線形ポリシーを持つ。
    """

    def __init__(
        self,
        n_members: int = 3,
        method: Literal["weighted_average", "majority_vote", "boltzmann_mix", "best_of_n"] = "weighted_average",
        persist_path: Optional[Path] = None,
    ):
        self._method = method
        self._persist_path = persist_path
        self._members: List[PolicyMember] = []
        self._decision_history: List[Dict[str, Any]] = []

        # 復元を試行
        self._restore()

        # メンバーが足りない場合、追加作成
        while len(self._members) < n_members:
            self._members.append(self._create_member(len(self._members)))

    def _create_member(self, member_id: int) -> PolicyMember:
        """ランダム初期化されたメンバーを作成"""
        rng = random.Random(42 + member_id * 7)
        theta = [
            [rng.gauss(0, 0.3) for _ in range(ACTION_DIM)]
            for _ in range(STATE_DIM)
        ]
        # バイアス: stay に少し寄せる
        bias = [-0.1, 0.15, -0.1]
        # 多様性のためメンバーごとに異なるバイアス
        bias = [b + rng.gauss(0, 0.1) for b in bias]
        temp = 0.8 + rng.random() * 0.8  # 0.8 ~ 1.6

        return PolicyMember(
            member_id=member_id,
            theta=theta,
            bias=bias,
            temperature=temp,
        )

    # ───────────────── ポリシー計算 ─────────────────

    def _compute_probs(self, member: PolicyMember, state: List[float]) -> Dict[str, float]:
        """1メンバーのソフトマックス確率分布を計算"""
        logits = list(member.bias)
        for j in range(ACTION_DIM):
            for i in range(min(STATE_DIM, len(state))):
                logits[j] += member.theta[i][j] * state[i]

        # temperature scaling
        logits = [l / max(member.temperature, 0.1) for l in logits]

        # softmax
        max_l = max(logits)
        exp_l = [math.exp(l - max_l) for l in logits]
        total = sum(exp_l)
        probs = [e / total for e in exp_l]

        return {ACTIONS[i]: probs[i] for i in range(ACTION_DIM)}

    def _select_action(self, probs: Dict[str, float]) -> str:
        """確率分布からアクションを選択 (argmax)"""
        return max(probs, key=probs.get)

    # ───────────────── アンサンブル決定 ─────────────────

    def decide(
        self,
        state: List[float],
        method: Optional[str] = None,
    ) -> EnsembleDecision:
        """
        アンサンブルで統合的な意思決定を行う。
        """
        m = method or self._method

        # 各メンバーの推奨を収集
        member_probs: List[Dict[str, float]] = []
        member_actions: List[str] = []
        votes_detail: List[Dict[str, Any]] = []

        for member in self._members:
            probs = self._compute_probs(member, state)
            action = self._select_action(probs)
            member_probs.append(probs)
            member_actions.append(action)
            votes_detail.append({
                "member_id": member.member_id,
                "action": action,
                "probs": {k: round(v, 4) for k, v in probs.items()},
                "avg_reward": round(member.avg_reward, 4),
            })

        # 集約手法に応じた統合
        if m == "majority_vote":
            final_probs, final_action = self._majority_vote(member_actions, member_probs)
        elif m == "boltzmann_mix":
            final_probs, final_action = self._boltzmann_mix(member_probs)
        elif m == "best_of_n":
            final_probs, final_action = self._best_of_n(member_probs)
        else:  # weighted_average
            final_probs, final_action = self._weighted_average(member_probs)

        # 合意度: 全員が同じアクションを選んだら 1.0
        vote_counts = {a: member_actions.count(a) for a in ACTIONS}
        max_votes = max(vote_counts.values()) if vote_counts else 0
        agreement = max_votes / max(1, len(self._members))

        # 信頼度: 最終確率のエントロピベース
        entropy = -sum(
            p * math.log(max(p, 1e-10)) for p in final_probs.values()
        )
        max_entropy = math.log(ACTION_DIM)
        confidence = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.5

        decision = EnsembleDecision(
            action=final_action,
            probabilities=final_probs,
            agreement=agreement,
            confidence=confidence,
            member_votes=votes_detail,
            method=m,
        )

        # メンバーのカウンタ更新
        for member, action in zip(self._members, member_actions):
            member.decision_count += 1
            if action == final_action:
                member.correct_count += 1

        # 履歴記録
        self._decision_history.append({
            "ts": datetime.now().isoformat(),
            "state": state,
            "action": final_action,
            "agreement": round(agreement, 4),
            "confidence": round(confidence, 4),
            "method": m,
        })
        if len(self._decision_history) > 200:
            self._decision_history = self._decision_history[-200:]

        self._persist()
        return decision

    # ───────────────── 集約手法 ─────────────────

    def _weighted_average(
        self,
        member_probs: List[Dict[str, float]],
    ) -> Tuple[Dict[str, float], str]:
        """パフォーマンス加重平均"""
        weights = []
        for member in self._members:
            # 報酬ベースの重み (最低 0.1 を保証)
            w = max(0.1, 0.5 + member.avg_reward)
            weights.append(w)
        total_w = sum(weights)

        avg_probs = {a: 0.0 for a in ACTIONS}
        for probs, w in zip(member_probs, weights):
            for a in ACTIONS:
                avg_probs[a] += probs.get(a, 0) * (w / total_w)

        action = max(avg_probs, key=avg_probs.get)
        return avg_probs, action

    def _majority_vote(
        self,
        member_actions: List[str],
        member_probs: List[Dict[str, float]],
    ) -> Tuple[Dict[str, float], str]:
        """多数決"""
        counts = {a: 0 for a in ACTIONS}
        for action in member_actions:
            counts[action] += 1

        total = len(member_actions)
        vote_probs = {a: counts[a] / max(1, total) for a in ACTIONS}
        action = max(counts, key=counts.get)
        return vote_probs, action

    def _boltzmann_mix(
        self,
        member_probs: List[Dict[str, float]],
    ) -> Tuple[Dict[str, float], str]:
        """Boltzmann 温度で信頼度加重混合"""
        temp = 0.5  # 低温 → 高パフォーマンスメンバーに寄る
        weights = []
        for member in self._members:
            score = member.avg_reward
            weights.append(math.exp(score / max(temp, 0.01)))
        total_w = sum(weights)

        mix = {a: 0.0 for a in ACTIONS}
        for probs, w in zip(member_probs, weights):
            for a in ACTIONS:
                mix[a] += probs.get(a, 0) * (w / total_w)

        action = max(mix, key=mix.get)
        return mix, action

    def _best_of_n(
        self,
        member_probs: List[Dict[str, float]],
    ) -> Tuple[Dict[str, float], str]:
        """最良メンバーの確率分布をそのまま使用"""
        best_idx = 0
        best_reward = -float("inf")
        for i, member in enumerate(self._members):
            if member.avg_reward > best_reward:
                best_reward = member.avg_reward
                best_idx = i

        probs = member_probs[best_idx]
        action = max(probs, key=probs.get)
        return probs, action

    # ───────────────── 学習 ─────────────────

    def update_rewards(self, reward: float) -> None:
        """
        全メンバーに報酬を記録。
        アンサンブル合意と同じアクションを選んだメンバーにはボーナス。
        """
        for member in self._members:
            # 合意ボーナス: 正解率に応じて加算
            bonus = 0.05 * member.accuracy if member.decision_count > 0 else 0
            member.total_reward += reward + bonus
        self._persist()

    def perturb_member(self, member_id: int, magnitude: float = 0.1) -> Dict[str, Any]:
        """
        指定メンバーのパラメータを摂動させて多様性を維持。
        """
        member = self._members[member_id] if member_id < len(self._members) else None
        if member is None:
            return {"error": f"member {member_id} not found"}

        rng = random.Random()
        for i in range(STATE_DIM):
            for j in range(ACTION_DIM):
                member.theta[i][j] += rng.gauss(0, magnitude)
        for j in range(ACTION_DIM):
            member.bias[j] += rng.gauss(0, magnitude * 0.5)

        self._persist()
        return {"member_id": member_id, "perturbed": True, "magnitude": magnitude}

    # ───────────────── 多様性指標 ─────────────────

    def get_diversity(self, state: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        メンバー間の多様性を測定。
        - action_entropy: 推奨アクションのエントロピ
        - weight_variance: パラメータの分散
        - agreement_history: 直近の合意率推移
        """
        test_state = state or [0.5, 0.5, 0.5]

        # 各メンバーの推奨アクション
        actions = []
        for member in self._members:
            probs = self._compute_probs(member, test_state)
            actions.append(self._select_action(probs))

        # アクションエントロピ
        counts = {a: actions.count(a) for a in ACTIONS}
        total = len(actions)
        action_entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                action_entropy -= p * math.log(p)

        # パラメータ分散
        flat_params = []
        for member in self._members:
            flat = []
            for row in member.theta:
                flat.extend(row)
            flat.extend(member.bias)
            flat_params.append(flat)

        param_variance = 0.0
        if flat_params:
            dim = len(flat_params[0])
            for d in range(dim):
                vals = [fp[d] for fp in flat_params]
                mean = sum(vals) / len(vals)
                param_variance += sum((v - mean) ** 2 for v in vals) / len(vals)
            param_variance /= dim

        # 合意履歴
        recent = self._decision_history[-20:] if self._decision_history else []
        agreement_trend = [e.get("agreement", 0) for e in recent]

        return {
            "action_entropy": round(action_entropy, 4),
            "max_entropy": round(math.log(ACTION_DIM), 4),
            "param_variance": round(param_variance, 6),
            "member_count": len(self._members),
            "agreement_trend": agreement_trend,
            "action_distribution": counts,
        }

    # ───────────────── 統計 ─────────────────

    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        members = []
        for m in self._members:
            members.append({
                "member_id": m.member_id,
                "avg_reward": round(m.avg_reward, 4),
                "accuracy": round(m.accuracy, 4),
                "decision_count": m.decision_count,
                "temperature": round(m.temperature, 4),
            })

        return {
            "member_count": len(self._members),
            "method": self._method,
            "total_decisions": len(self._decision_history),
            "members": members,
            "diversity": self.get_diversity(),
        }

    # ───────────────── 永続化 ─────────────────

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "method": self._method,
                "members": [
                    {
                        "member_id": m.member_id,
                        "theta": m.theta,
                        "bias": m.bias,
                        "temperature": m.temperature,
                        "total_reward": m.total_reward,
                        "decision_count": m.decision_count,
                        "correct_count": m.correct_count,
                    }
                    for m in self._members
                ],
                "decision_history": self._decision_history[-200:],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("ensemble persist failed: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            self._method = data.get("method", self._method)
            self._members = []
            for mdata in data.get("members", []):
                member = PolicyMember(
                    member_id=mdata["member_id"],
                    theta=mdata["theta"],
                    bias=mdata["bias"],
                    temperature=mdata.get("temperature", 1.0),
                    total_reward=mdata.get("total_reward", 0),
                    decision_count=mdata.get("decision_count", 0),
                    correct_count=mdata.get("correct_count", 0),
                )
                self._members.append(member)
            self._decision_history = data.get("decision_history", [])
        except Exception as e:
            _log.warning("ensemble restore failed: %s", e)
