"""
Policy Gradient Estimator — REINFORCE ベースの方策勾配推定
================================================================
難易度遷移を「方策」、スコアを「報酬」として扱い、
REINFORCE スタイルで行動確率を更新する。

状態:  (success_rate, avg_score, current_difficulty_idx)
行動:  stay / level_up / level_down
報酬:  タスクスコア (0-1)

特徴:
  1) Softmax 方策  (温度パラメータ付き)
  2) ベースライン減算で分散低減
  3) エントロピーボーナスで探索維持
  4) 軌跡バッファによる遅延更新
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─── 定数 ───
ACTIONS = ["level_down", "stay", "level_up"]
DIFFICULTIES = ["concrete", "guided", "standard", "abstract"]

ACTION_IDX = {a: i for i, a in enumerate(ACTIONS)}
DIFF_IDX = {d: i for i, d in enumerate(DIFFICULTIES)}


@dataclass
class Trajectory:
    """1 ステップの軌跡"""
    state: List[float]           # [success_rate, avg_score, diff_idx_normalized]
    action: str                  # level_down / stay / level_up
    reward: float                # task score
    log_prob: float              # 選択時の log π(a|s)
    cycle: int = 0
    ts: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Trajectory":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class PolicySnapshot:
    """方策パラメータのスナップショット"""
    theta: List[List[float]]     # [state_dim x action_dim] — linear weights
    bias: List[float]            # [action_dim]
    baseline: float              # running average reward baseline
    update_count: int
    entropy_coeff: float
    learning_rate: float
    temperature: float

    def to_dict(self) -> dict:
        return asdict(self)


class PolicyGradient:
    """
    Softmax 線形方策 + REINFORCE 勾配更新。

    π(a|s) = softmax(θᵀs + b) / τ

    更新:
      θ += α · (R - b) · ∇_θ log π(a|s) + β · H(π)
    """

    STATE_DIM = 3   # success_rate, avg_score, difficulty_idx (normalized 0-1)
    ACTION_DIM = 3  # level_down, stay, level_up

    def __init__(
        self,
        learning_rate: float = 0.01,
        temperature: float = 1.0,
        entropy_coeff: float = 0.01,
        baseline_decay: float = 0.95,
        max_trajectory: int = 200,
        persist_path: Optional[Path] = None,
    ):
        self.lr = learning_rate
        self.temperature = temperature
        self.entropy_coeff = entropy_coeff
        self.baseline_decay = baseline_decay
        self.max_trajectory = max_trajectory
        self._persist_path = persist_path

        # パラメータ初期化 (small random-ish — 全ゼロだと softmax 均等)
        # stay にわずかなバイアスを与える (安定寄り初期方策)
        self.theta: List[List[float]] = [
            [0.0, 0.0, 0.0] for _ in range(self.STATE_DIM)
        ]
        self.bias: List[float] = [-0.1, 0.2, -0.1]  # stay を初期優勢に

        self.baseline: float = 0.5  # 期待報酬ベースライン
        self._update_count: int = 0
        self._trajectories: List[Trajectory] = []

        # 永続化から復元
        self._restore()

    # ═══════════════════════════════════════════════════════
    # 状態エンコーディング
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def encode_state(
        success_rate: float,
        avg_score: float,
        difficulty: str,
    ) -> List[float]:
        """環境状態を数値ベクトルに変換"""
        diff_idx = DIFF_IDX.get(difficulty, 2)
        return [
            max(0.0, min(1.0, success_rate)),
            max(0.0, min(1.0, avg_score)),
            diff_idx / 3.0,  # 0-1 正規化
        ]

    # ═══════════════════════════════════════════════════════
    # Softmax 方策
    # ═══════════════════════════════════════════════════════
    def _logits(self, state: List[float]) -> List[float]:
        """θᵀs + b"""
        logits = list(self.bias)
        for j in range(self.ACTION_DIM):
            for i in range(self.STATE_DIM):
                logits[j] += self.theta[i][j] * state[i]
        return logits

    def _softmax(self, logits: List[float]) -> List[float]:
        """温度付き softmax"""
        scaled = [x / max(self.temperature, 0.01) for x in logits]
        max_val = max(scaled)
        exps = [math.exp(x - max_val) for x in scaled]
        total = sum(exps)
        return [e / total for e in exps]

    def get_action_probs(self, state: List[float]) -> Dict[str, float]:
        """各アクションの確率を返す"""
        probs = self._softmax(self._logits(state))
        return {ACTIONS[i]: round(probs[i], 6) for i in range(self.ACTION_DIM)}

    def select_action(self, state: List[float]) -> Tuple[str, float]:
        """
        方策に従ってアクションをサンプリング。
        Returns: (action_name, log_prob)
        """
        probs = self._softmax(self._logits(state))
        # Weighted random selection
        import random
        r = random.random()
        cumulative = 0.0
        chosen_idx = len(probs) - 1
        for i, p in enumerate(probs):
            cumulative += p
            if r < cumulative:
                chosen_idx = i
                break
        log_prob = math.log(max(probs[chosen_idx], 1e-10))
        return ACTIONS[chosen_idx], log_prob

    # ═══════════════════════════════════════════════════════
    # 軌跡記録と勾配更新
    # ═══════════════════════════════════════════════════════
    def record(
        self,
        state: List[float],
        action: str,
        reward: float,
        log_prob: float,
        cycle: int = 0,
    ) -> None:
        """1 ステップの軌跡を記録"""
        self._trajectories.append(Trajectory(
            state=state,
            action=action,
            reward=reward,
            log_prob=log_prob,
            cycle=cycle,
        ))
        # リングバッファ
        if len(self._trajectories) > self.max_trajectory:
            self._trajectories = self._trajectories[-self.max_trajectory:]

    def update(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """
        蓄積された軌跡で REINFORCE 更新を実行。

        θ += α · Σ_t (R_t - b) · ∇_θ log π(a_t|s_t)
        """
        batch = self._trajectories[-(batch_size or len(self._trajectories)):]
        if not batch:
            return {"updated": False, "reason": "no_trajectories"}

        # ベースライン更新
        rewards = [t.reward for t in batch]
        avg_reward = sum(rewards) / len(rewards)
        self.baseline = self.baseline_decay * self.baseline + (1 - self.baseline_decay) * avg_reward

        # 勾配蓄積
        grad_theta = [[0.0] * self.ACTION_DIM for _ in range(self.STATE_DIM)]
        grad_bias = [0.0] * self.ACTION_DIM

        for traj in batch:
            advantage = traj.reward - self.baseline
            probs = self._softmax(self._logits(traj.state))
            action_idx = ACTION_IDX.get(traj.action, 1)

            # ∇ log π = (1_{a=j} - π_j) — softmax gradient
            for j in range(self.ACTION_DIM):
                indicator = 1.0 if j == action_idx else 0.0
                grad_j = indicator - probs[j]
                # θ_ij の勾配 = advantage * grad_j * s_i
                for i in range(self.STATE_DIM):
                    grad_theta[i][j] += advantage * grad_j * traj.state[i]
                grad_bias[j] += advantage * grad_j

            # エントロピーボーナス勾配: H = -Σ π log π
            # ∇H = -Σ (1 + log π_j) · ∇π_j
            if self.entropy_coeff > 0:
                for j in range(self.ACTION_DIM):
                    ent_grad = -(1.0 + math.log(max(probs[j], 1e-10)))
                    ent_correction = ent_grad * (1.0 if j == action_idx else 0.0 - probs[j])
                    for i in range(self.STATE_DIM):
                        grad_theta[i][j] += self.entropy_coeff * ent_correction * traj.state[i]
                    grad_bias[j] += self.entropy_coeff * ent_correction

        # 勾配適用 (バッチ平均)
        n = len(batch)
        for i in range(self.STATE_DIM):
            for j in range(self.ACTION_DIM):
                self.theta[i][j] += self.lr * grad_theta[i][j] / n
        for j in range(self.ACTION_DIM):
            self.bias[j] += self.lr * grad_bias[j] / n

        self._update_count += 1
        self._persist()

        return {
            "updated": True,
            "batch_size": n,
            "avg_reward": round(avg_reward, 4),
            "baseline": round(self.baseline, 4),
            "update_count": self._update_count,
            "entropy": round(self._entropy(batch[-1].state), 4),
        }

    def _entropy(self, state: List[float]) -> float:
        """方策のエントロピー H(π)"""
        probs = self._softmax(self._logits(state))
        return -sum(p * math.log(max(p, 1e-10)) for p in probs)

    # ═══════════════════════════════════════════════════════
    # 推薦 (greedy)
    # ═══════════════════════════════════════════════════════
    def recommend_action(self, state: List[float]) -> Dict[str, Any]:
        """
        現在の方策で最良アクション (greedy) を返す。
        """
        probs = self.get_action_probs(state)
        best_action = max(probs, key=probs.get)
        return {
            "action": best_action,
            "probs": probs,
            "entropy": round(self._entropy(state), 4),
            "baseline": round(self.baseline, 4),
            "update_count": self._update_count,
        }

    # ═══════════════════════════════════════════════════════
    # スナップショット / 統計
    # ═══════════════════════════════════════════════════════
    def get_snapshot(self) -> Dict[str, Any]:
        """方策パラメータ + 統計のスナップショット"""
        snap = PolicySnapshot(
            theta=self.theta,
            bias=self.bias,
            baseline=round(self.baseline, 4),
            update_count=self._update_count,
            entropy_coeff=self.entropy_coeff,
            learning_rate=self.lr,
            temperature=self.temperature,
        )
        # 代表状態での方策分布
        sample_states = {
            "low_performance": self.encode_state(0.3, 0.3, "standard"),
            "mid_performance": self.encode_state(0.6, 0.6, "standard"),
            "high_performance": self.encode_state(0.9, 0.85, "abstract"),
        }
        policy_samples = {
            name: self.get_action_probs(s)
            for name, s in sample_states.items()
        }
        return {
            **snap.to_dict(),
            "trajectory_count": len(self._trajectories),
            "policy_samples": policy_samples,
        }

    def get_stats(self) -> Dict[str, Any]:
        """軽量統計"""
        recent = self._trajectories[-20:]
        if not recent:
            return {
                "trajectory_count": 0,
                "update_count": self._update_count,
                "baseline": round(self.baseline, 4),
            }
        rewards = [t.reward for t in recent]
        actions = [t.action for t in recent]
        action_dist = {}
        for a in ACTIONS:
            action_dist[a] = sum(1 for x in actions if x == a)
        return {
            "trajectory_count": len(self._trajectories),
            "update_count": self._update_count,
            "baseline": round(self.baseline, 4),
            "recent_avg_reward": round(sum(rewards) / len(rewards), 4),
            "recent_action_dist": action_dist,
        }

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "theta": self.theta,
                "bias": self.bias,
                "baseline": self.baseline,
                "update_count": self._update_count,
                "lr": self.lr,
                "temperature": self.temperature,
                "entropy_coeff": self.entropy_coeff,
                "trajectories": [t.to_dict() for t in self._trajectories[-self.max_trajectory:]],
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
            self.theta = data.get("theta", self.theta)
            self.bias = data.get("bias", self.bias)
            self.baseline = data.get("baseline", self.baseline)
            self._update_count = data.get("update_count", 0)
            # 軌跡復元
            raw_trajs = data.get("trajectories", [])
            self._trajectories = [Trajectory.from_dict(t) for t in raw_trajs]
        except Exception:
            pass
