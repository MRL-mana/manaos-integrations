#!/usr/bin/env python3
"""
Curiosity-Driven Exploration — 好奇心駆動型探索エンジン (Round 9)
================================================================
内発的動機付けにより、エージェントが未知の状態・行動パターンを
積極的に探索するよう誘導する。

主要概念:
  - State Visitation Count: 状態空間の訪問回数を追跡
  - Prediction Error: 予測誤差ベースの好奇心ボーナス
  - Novelty Detection: 新規パターンの検出
  - Exploration Budget: 探索予算管理
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("rl_anything.curiosity")

# ── 定数 ──
MAX_STATE_HISTORY = 2000
NOVELTY_DECAY = 0.95          # 新規性の減衰係数
PREDICTION_LR = 0.1           # 予測モデルの学習率
CURIOSITY_SCALE = 0.3         # 好奇心ボーナスのスケール
MIN_VISITS_FOR_FAMILIAR = 5   # 「見慣れた」とみなす訪問回数
EXPLORATION_BUDGET_DEFAULT = 100  # デフォルト探索バジェット


@dataclass
class StateVisit:
    """状態訪問記録"""
    state_hash: str
    visit_count: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0
    last_visit_cycle: int = 0
    first_visit_cycle: int = 0
    novelty_score: float = 1.0  # 初回は最大新規性

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CuriositySignal:
    """好奇心シグナル — 1サイクル分の探索情報"""
    cycle: int
    state_hash: str
    visit_count: int
    novelty: float
    prediction_error: float
    curiosity_bonus: float
    is_novel: bool
    exploration_rate: float
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExplorationBudget:
    """探索バジェット管理"""
    total: int = EXPLORATION_BUDGET_DEFAULT
    used: int = 0
    novel_discoveries: int = 0
    wasted: int = 0  # 既知状態への再探索

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    @property
    def efficiency(self) -> float:
        if self.used == 0:
            return 0.0
        return self.novel_discoveries / self.used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "used": self.used,
            "remaining": self.remaining,
            "novel_discoveries": self.novel_discoveries,
            "wasted": self.wasted,
            "efficiency": round(self.efficiency, 4),
        }


class CuriosityExplorer:
    """
    好奇心駆動型探索エンジン。
    
    - 状態訪問カウントで新規性を判定
    - 予測誤差をベースとした好奇心ボーナスを計算
    - 探索バジェットを管理
    - 新規パターン発見時にイベントを生成
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        cfg = (config or {}).get("curiosity", {})
        self._persist_path = persist_path

        # 設定
        self.novelty_decay = cfg.get("novelty_decay", NOVELTY_DECAY)
        self.prediction_lr = cfg.get("prediction_lr", PREDICTION_LR)
        self.curiosity_scale = cfg.get("curiosity_scale", CURIOSITY_SCALE)
        self.min_visits_familiar = cfg.get("min_visits_familiar", MIN_VISITS_FOR_FAMILIAR)

        # 状態訪問テーブル: hash → StateVisit
        self._visits: Dict[str, StateVisit] = {}
        # 予測モデル: state_hash → predicted_reward
        self._predictions: Dict[str, float] = {}
        # 好奇心シグナル履歴
        self._signals: List[CuriositySignal] = []
        # 探索バジェット
        self.budget = ExplorationBudget(
            total=cfg.get("exploration_budget", EXPLORATION_BUDGET_DEFAULT)
        )
        # 統計
        self._total_visits = 0
        self._novel_count = 0

        self._restore()

    # ═══════════════════════════════════════════════════════
    # 状態ハッシュ生成
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def hash_state(
        difficulty: str,
        outcome: str,
        tool_names: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> str:
        """
        状態をコンパクトなハッシュに変換。
        同じ状態コンテキストは同じハッシュを生成する。
        """
        components = [
            str(difficulty),
            outcome,
            ",".join(sorted(tool_names or [])),
            domain or "unknown",
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ═══════════════════════════════════════════════════════
    # 探索シグナル計算
    # ═══════════════════════════════════════════════════════
    def observe(
        self,
        state_hash: str,
        actual_reward: float,
        cycle: int,
    ) -> CuriositySignal:
        """
        状態を観測し、好奇心シグナルを生成。
        
        Returns:
            CuriositySignal: 今回の探索情報
        """
        # 訪問記録の更新
        if state_hash not in self._visits:
            visit = StateVisit(
                state_hash=state_hash,
                visit_count=0,
                first_visit_cycle=cycle,
            )
            self._visits[state_hash] = visit
            is_novel = True
            self._novel_count += 1
            self.budget.novel_discoveries += 1
        else:
            visit = self._visits[state_hash]
            is_novel = visit.visit_count < self.min_visits_familiar

        visit.visit_count += 1
        visit.total_reward += actual_reward
        visit.avg_reward = visit.total_reward / visit.visit_count
        visit.last_visit_cycle = cycle
        self._total_visits += 1
        self.budget.used += 1

        # 訪問回数ベースの新規性スコア
        novelty = 1.0 / math.sqrt(visit.visit_count)
        visit.novelty_score = novelty

        # 予測誤差ベースの好奇心
        predicted = self._predictions.get(state_hash, 0.5)  # デフォルト予測 0.5
        prediction_error = abs(actual_reward - predicted)

        # 予測モデルの更新 (exponential moving average)
        self._predictions[state_hash] = (
            predicted + self.prediction_lr * (actual_reward - predicted)
        )

        # 好奇心ボーナス = novelty * prediction_error * scale
        curiosity_bonus = novelty * prediction_error * self.curiosity_scale

        # 探索率 = ユニーク状態数 / 総訪問数
        unique_states = len(self._visits)
        exploration_rate = unique_states / max(1, self._total_visits)

        # バジェットの浪費カウント
        if not is_novel and visit.visit_count > self.min_visits_familiar * 2:
            self.budget.wasted += 1

        signal = CuriositySignal(
            cycle=cycle,
            state_hash=state_hash,
            visit_count=visit.visit_count,
            novelty=round(novelty, 6),
            prediction_error=round(prediction_error, 6),
            curiosity_bonus=round(curiosity_bonus, 6),
            is_novel=is_novel,
            exploration_rate=round(exploration_rate, 6),
        )

        self._signals.append(signal)
        # 履歴上限
        if len(self._signals) > MAX_STATE_HISTORY:
            self._signals = self._signals[-MAX_STATE_HISTORY:]

        self._persist()
        return signal

    # ═══════════════════════════════════════════════════════
    # 探索推薦
    # ═══════════════════════════════════════════════════════
    def recommend_exploration(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        探索優先度の高い状態を推薦。
        訪問回数が少なく、予測誤差が大きい状態を優先。
        """
        scored: List[Tuple[float, str, StateVisit]] = []
        for h, v in self._visits.items():
            pred_err = abs(v.avg_reward - self._predictions.get(h, 0.5))
            priority = v.novelty_score * (1.0 + pred_err)
            scored.append((priority, h, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        recommendations = []
        for priority, h, v in scored[:top_k]:
            recommendations.append({
                "state_hash": h,
                "priority": round(priority, 4),
                "visit_count": v.visit_count,
                "novelty": round(v.novelty_score, 4),
                "avg_reward": round(v.avg_reward, 4),
                "predicted_reward": round(self._predictions.get(h, 0.5), 4),
            })
        return recommendations

    # ═══════════════════════════════════════════════════════
    # 新規性マップ
    # ═══════════════════════════════════════════════════════
    def get_novelty_map(self) -> Dict[str, Any]:
        """
        全状態の新規性マップを返す。
        フロントエンドの可視化用。
        """
        states = []
        for h, v in self._visits.items():
            states.append({
                "state_hash": h,
                "visit_count": v.visit_count,
                "novelty": round(v.novelty_score, 4),
                "avg_reward": round(v.avg_reward, 4),
                "is_familiar": v.visit_count >= self.min_visits_familiar,
                "first_cycle": v.first_visit_cycle,
                "last_cycle": v.last_visit_cycle,
            })

        # 新規性で降順ソート
        states.sort(key=lambda x: x["novelty"], reverse=True)

        familiar_count = sum(1 for s in states if s["is_familiar"])
        novel_count = len(states) - familiar_count

        return {
            "states": states,
            "total_states": len(states),
            "familiar_count": familiar_count,
            "novel_count": novel_count,
            "coverage": round(len(states) / max(1, self._total_visits), 4),
        }

    # ═══════════════════════════════════════════════════════
    # 探索統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """探索統計サマリー"""
        unique = len(self._visits)
        recent_signals = self._signals[-20:] if self._signals else []
        recent_novelty = (
            sum(s.novelty for s in recent_signals) / len(recent_signals)
            if recent_signals else 0.0
        )
        recent_curiosity = (
            sum(s.curiosity_bonus for s in recent_signals) / len(recent_signals)
            if recent_signals else 0.0
        )

        return {
            "total_visits": self._total_visits,
            "unique_states": unique,
            "novel_discoveries": self._novel_count,
            "exploration_rate": round(unique / max(1, self._total_visits), 4),
            "recent_avg_novelty": round(recent_novelty, 4),
            "recent_avg_curiosity": round(recent_curiosity, 4),
            "budget": self.budget.to_dict(),
            "signal_count": len(self._signals),
        }

    def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """直近の好奇心シグナルを返す"""
        return [s.to_dict() for s in self._signals[-limit:]]

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "visits": {h: v.to_dict() for h, v in self._visits.items()},
                "predictions": self._predictions,
                "budget": self.budget.to_dict(),
                "total_visits": self._total_visits,
                "novel_count": self._novel_count,
                "signals": [s.to_dict() for s in self._signals[-200:]],  # 直近200件
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("curiosity persist error: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            # 訪問テーブル復元
            for h, v_dict in data.get("visits", {}).items():
                self._visits[h] = StateVisit(**v_dict)
            self._predictions = data.get("predictions", {})
            self._total_visits = data.get("total_visits", 0)
            self._novel_count = data.get("novel_count", 0)
            # バジェット復元
            b = data.get("budget", {})
            self.budget.used = b.get("used", 0)
            self.budget.novel_discoveries = b.get("novel_discoveries", 0)
            self.budget.wasted = b.get("wasted", 0)
            # シグナル復元
            for s_dict in data.get("signals", []):
                self._signals.append(CuriositySignal(**s_dict))
        except Exception as e:
            _log.warning("curiosity restore error: %s", e)
