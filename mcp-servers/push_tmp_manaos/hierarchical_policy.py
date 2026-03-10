#!/usr/bin/env python3
"""
Hierarchical Policy — 階層型方策エンジン (Round 9)
===================================================
Options Framework に基づく階層的意思決定。

構造:
  Manager (上位方策)  → サブゴール（Option）を選択
  Worker  (下位方策)  → 選択されたOption内でアクションを実行
  Termination         → Option完了条件を判定

利点:
  - 時間的抽象化：長期戦略と短期行動の分離
  - 再利用性：学習したOptionを異なるタスクで再利用
  - スケーラビリティ：複雑な問題の分割統治
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("rl_anything.hierarchical")

# ── 定数 ──
MAX_OPTIONS = 20
MAX_HISTORY = 500
OPTION_TEMPERATURE = 1.0
WORKER_TEMPERATURE = 0.8
TERMINATION_THRESHOLD = 0.6
ACTIONS = ["level_down", "stay", "level_up"]
ACTION_DIM = len(ACTIONS)


@dataclass
class Option:
    """
    Options Framework の1オプション。
    マネージャーが選択するサブゴール単位。
    """
    option_id: str
    name: str
    description: str = ""
    # 開始条件: 適用可能な難易度レベル
    applicable_difficulties: List[str] = field(default_factory=lambda: [
        "concrete", "guided", "standard", "abstract"
    ])
    # ワーカーの行動選好 (action_dim ベクトル)
    action_preferences: List[float] = field(default_factory=lambda: [0.33, 0.34, 0.33])
    # 終了確率（サイクルごとに終了する確率）
    termination_prob: float = 0.3
    # パフォーマンス追跡
    times_selected: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = round(self.success_rate, 4)
        return d


@dataclass
class HierarchicalDecision:
    """階層的意思決定の結果"""
    option_id: str
    option_name: str
    action: str
    option_prob: float
    action_prob: float
    should_terminate: bool
    level: str  # "manager" or "worker"
    confidence: float
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── デフォルトOptions ──
DEFAULT_OPTIONS = [
    Option(
        option_id="consolidate",
        name="習熟強化",
        description="現在の難易度で成功率を上げる",
        action_preferences=[0.15, 0.70, 0.15],
        termination_prob=0.2,
    ),
    Option(
        option_id="explore_up",
        name="上位探索",
        description="より高い難易度に挑戦",
        action_preferences=[0.05, 0.25, 0.70],
        termination_prob=0.4,
    ),
    Option(
        option_id="recover",
        name="回復",
        description="難易度を下げて安定化",
        action_preferences=[0.70, 0.25, 0.05],
        termination_prob=0.3,
    ),
    Option(
        option_id="balanced",
        name="バランス",
        description="状況に応じて柔軟に対応",
        action_preferences=[0.25, 0.50, 0.25],
        termination_prob=0.35,
    ),
]


class HierarchicalPolicy:
    """
    階層型方策エンジン。
    
    Manager: ソフトマックスでOptionを選択
    Worker: 選択されたOptionの行動選好に基づきアクション決定
    Termination: 確率的にOption終了を判定
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        cfg = (config or {}).get("hierarchical", {})
        self._persist_path = persist_path

        # 温度パラメータ
        self.manager_temperature = cfg.get("manager_temperature", OPTION_TEMPERATURE)
        self.worker_temperature = cfg.get("worker_temperature", WORKER_TEMPERATURE)
        self.termination_threshold = cfg.get("termination_threshold", TERMINATION_THRESHOLD)

        # Options（サブゴール）
        self._options: Dict[str, Option] = {}
        for opt in DEFAULT_OPTIONS:
            self._options[opt.option_id] = Option(**asdict(opt))

        # 現在アクティブなOption
        self._active_option_id: Optional[str] = None
        self._active_since_cycle: int = 0
        self._active_steps: int = 0

        # マネージャーの選好ウェイト (option_id → weight)
        self._manager_weights: Dict[str, float] = {
            oid: 1.0 for oid in self._options
        }

        # 意思決定履歴
        self._history: List[HierarchicalDecision] = []

        # 統計
        self._total_decisions = 0
        self._option_switches = 0

        self._restore()

    # ═══════════════════════════════════════════════════════
    # マネージャー: Option選択
    # ═══════════════════════════════════════════════════════
    def _select_option(self, difficulty: str) -> str:
        """
        マネージャーがOptionを選択。
        適用可能なOptionからソフトマックスで選ぶ。
        """
        applicable = {
            oid: opt for oid, opt in self._options.items()
            if difficulty in opt.applicable_difficulties
        }
        if not applicable:
            applicable = dict(self._options)

        # ソフトマックス計算
        weights = {}
        for oid, opt in applicable.items():
            w = self._manager_weights.get(oid, 1.0)
            # 成功率ボーナス
            w += opt.success_rate * 0.5
            weights[oid] = w

        max_w = max(weights.values()) if weights else 0
        exp_w = {}
        for oid, w in weights.items():
            exp_w[oid] = math.exp((w - max_w) / max(0.01, self.manager_temperature))

        total = sum(exp_w.values())
        probs = {oid: v / total for oid, v in exp_w.items()}

        # サンプリング
        r = random.random()
        cumsum = 0.0
        selected = list(probs.keys())[0]
        for oid, p in probs.items():
            cumsum += p
            if r <= cumsum:
                selected = oid
                break

        return selected

    # ═══════════════════════════════════════════════════════
    # ワーカー: アクション選択
    # ═══════════════════════════════════════════════════════
    def _select_action(self, option: Option, state: Optional[List[float]] = None) -> Tuple[str, float]:
        """
        ワーカーがOptionの行動選好に基づきアクション決定。
        """
        prefs = option.action_preferences
        # 温度付きソフトマックス
        max_p = max(prefs)
        exp_p = [math.exp((p - max_p) / max(0.01, self.worker_temperature)) for p in prefs]
        total = sum(exp_p)
        probs = [v / total for v in exp_p]

        # サンプリング
        r = random.random()
        cumsum = 0.0
        idx = 0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                idx = i
                break

        return ACTIONS[idx], probs[idx]

    # ═══════════════════════════════════════════════════════
    # 終了判定
    # ═══════════════════════════════════════════════════════
    def _should_terminate(self, option: Option) -> bool:
        """確率的にオプション終了を判定"""
        # 長く続いたOptionほど終了確率UP
        step_factor = min(2.0, 1.0 + self._active_steps * 0.1)
        adjusted_prob = min(0.95, option.termination_prob * step_factor)
        return random.random() < adjusted_prob

    # ═══════════════════════════════════════════════════════
    # 統合意思決定
    # ═══════════════════════════════════════════════════════
    def decide(
        self,
        difficulty: str = "standard",
        state: Optional[List[float]] = None,
        cycle: int = 0,
    ) -> HierarchicalDecision:
        """
        階層的意思決定を実行。
        
        1. アクティブOptionの終了判定
        2. 必要ならマネージャーが新Optionを選択
        3. ワーカーがアクション実行
        """
        self._total_decisions += 1

        # 1. 終了判定
        need_new_option = False
        if self._active_option_id is None:
            need_new_option = True
        else:
            active_opt = self._options.get(self._active_option_id)
            if active_opt and self._should_terminate(active_opt):
                need_new_option = True

        # 2. マネージャー選択
        if need_new_option:
            old_id = self._active_option_id
            self._active_option_id = self._select_option(difficulty)
            self._active_since_cycle = cycle
            self._active_steps = 0
            if old_id is not None and old_id != self._active_option_id:
                self._option_switches += 1

        # 3. ワーカー行動
        option = self._options[self._active_option_id]  # type: ignore
        option.times_selected += 1
        self._active_steps += 1

        action, action_prob = self._select_action(option, state)

        # Option選択確率の計算
        total_w = sum(self._manager_weights.get(oid, 1.0) for oid in self._options)
        option_prob = self._manager_weights.get(self._active_option_id, 1.0) / max(1.0, total_w)  # type: ignore[call-arg]

        # 信頼度 = option_prob * action_prob
        confidence = option_prob * action_prob

        decision = HierarchicalDecision(
            option_id=self._active_option_id,  # type: ignore
            option_name=option.name,
            action=action,
            option_prob=round(option_prob, 4),
            action_prob=round(action_prob, 4),
            should_terminate=need_new_option,
            level="manager" if need_new_option else "worker",
            confidence=round(confidence, 4),
        )

        self._history.append(decision)
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

        self._persist()
        return decision

    # ═══════════════════════════════════════════════════════
    # 報酬フィードバック
    # ═══════════════════════════════════════════════════════
    def update_reward(self, reward: float, outcome: str = "unknown") -> None:
        """
        直近の意思決定に報酬をフィードバック。
        Optionのパフォーマンスとマネージャーウェイトを更新。
        """
        if self._active_option_id is None:
            return

        opt = self._options.get(self._active_option_id)
        if opt is None:
            return

        opt.total_reward += reward
        opt.avg_reward = opt.total_reward / max(1, opt.times_selected)

        if outcome == "success":
            opt.success_count += 1
        elif outcome == "failure":
            opt.failure_count += 1

        # マネージャーウェイトの更新 (exponential moving average)
        old_w = self._manager_weights.get(self._active_option_id, 1.0)
        self._manager_weights[self._active_option_id] = old_w + 0.1 * (reward - old_w)

        self._persist()

    # ═══════════════════════════════════════════════════════
    # Option管理
    # ═══════════════════════════════════════════════════════
    def add_option(
        self,
        option_id: str,
        name: str,
        description: str = "",
        action_preferences: Optional[List[float]] = None,
        termination_prob: float = 0.3,
    ) -> Option:
        """カスタムOptionを追加"""
        if len(self._options) >= MAX_OPTIONS:
            # 最もパフォーマンスの低いOptionを削除
            worst = min(
                self._options.values(),
                key=lambda o: o.avg_reward if o.times_selected > 0 else float("inf"),
            )
            if worst.option_id not in ("consolidate", "explore_up", "recover", "balanced"):
                del self._options[worst.option_id]
                self._manager_weights.pop(worst.option_id, None)

        prefs = action_preferences or [0.33, 0.34, 0.33]
        # 正規化
        total = sum(prefs)
        prefs = [p / total for p in prefs] if total > 0 else [1/3]*3

        opt = Option(
            option_id=option_id,
            name=name,
            description=description,
            action_preferences=prefs,
            termination_prob=termination_prob,
        )
        self._options[option_id] = opt
        self._manager_weights[option_id] = 1.0

        self._persist()
        return opt

    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """全Optionの情報"""
        return {oid: opt.to_dict() for oid, opt in self._options.items()}

    def get_active_option(self) -> Optional[Dict[str, Any]]:
        """現在アクティブなOption"""
        if self._active_option_id is None:
            return None
        opt = self._options.get(self._active_option_id)
        if opt is None:
            return None
        return {
            **opt.to_dict(),
            "active_since_cycle": self._active_since_cycle,
            "active_steps": self._active_steps,
        }

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """階層型方策の統計"""
        options_summary = []
        for oid, opt in self._options.items():
            options_summary.append({
                "option_id": oid,
                "name": opt.name,
                "times_selected": opt.times_selected,
                "avg_reward": round(opt.avg_reward, 4),
                "success_rate": round(opt.success_rate, 4),
                "manager_weight": round(self._manager_weights.get(oid, 1.0), 4),
            })

        active = self.get_active_option()

        return {
            "total_decisions": self._total_decisions,
            "option_switches": self._option_switches,
            "option_count": len(self._options),
            "options": options_summary,
            "active_option": active,
            "history_size": len(self._history),
        }

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """直近の意思決定履歴"""
        return [h.to_dict() for h in self._history[-limit:]]

    def get_option_performance(self) -> Dict[str, Any]:
        """Option別パフォーマンス比較"""
        performance = {}
        for oid, opt in self._options.items():
            performance[oid] = {
                "name": opt.name,
                "times_selected": opt.times_selected,
                "avg_reward": round(opt.avg_reward, 4),
                "success_rate": round(opt.success_rate, 4),
                "total_reward": round(opt.total_reward, 4),
                "success_count": opt.success_count,
                "failure_count": opt.failure_count,
            }
        return performance

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "options": {oid: opt.to_dict() for oid, opt in self._options.items()},
                "manager_weights": self._manager_weights,
                "active_option_id": self._active_option_id,
                "active_since_cycle": self._active_since_cycle,
                "active_steps": self._active_steps,
                "total_decisions": self._total_decisions,
                "option_switches": self._option_switches,
                "history": [h.to_dict() for h in self._history[-100:]],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("hierarchical persist error: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))

            # Options復元
            for oid, o_dict in data.get("options", {}).items():
                o_dict.pop("success_rate", None)  # computed property
                self._options[oid] = Option(**o_dict)

            self._manager_weights = data.get("manager_weights", {})
            self._active_option_id = data.get("active_option_id")
            self._active_since_cycle = data.get("active_since_cycle", 0)
            self._active_steps = data.get("active_steps", 0)
            self._total_decisions = data.get("total_decisions", 0)
            self._option_switches = data.get("option_switches", 0)

            for h_dict in data.get("history", []):
                self._history.append(HierarchicalDecision(**h_dict))
        except Exception as e:
            _log.warning("hierarchical restore error: %s", e)
