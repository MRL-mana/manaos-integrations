"""
Meta-Controller — RL システムの自己チューニング
================================================================
RL パイプラインのハイパーパラメータを、パフォーマンス指標に
基づいて動的に調整する。

対象パラメータ:
  1) 方策勾配の学習率 (lr)
  2) 方策の温度 (temperature)
  3) カリキュラムの閾値 (up/down threshold)
  4) 異常検知の感度 (z_threshold)
  5) リプレイバッファの優先度指数

メタ指標:
  - 学習安定性 (score のスライディング分散)
  - 収束速度 (スコア改善率)
  - 探索・活用バランス (方策エントロピー)
  - 異常率 (直近のアラート頻度)
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MetaAdjustment:
    """1 回のメタ調整結果"""
    param_name: str
    old_value: float
    new_value: float
    reason: str
    meta_signal: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetaReport:
    """メタ調整レポート"""
    adjustments: List[MetaAdjustment]
    meta_signals: Dict[str, float]
    health_score: float          # 0-1: システム全体の健全度
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "adjustments": [a.to_dict() for a in self.adjustments],
            "meta_signals": {k: round(v, 4) for k, v in self.meta_signals.items()},
            "health_score": round(self.health_score, 4),
            "recommendations": self.recommendations,
        }


class MetaController:
    """
    メタ学習コントローラ。
    analyze() で現状を分析し、tune() でパラメータを自動調整。
    """

    # スライディングウィンドウ
    WINDOW = 20
    SHORT_WINDOW = 5

    # 調整ステップ
    LR_STEP = 0.002
    TEMP_STEP = 0.1
    THRESHOLD_STEP = 0.05
    ZSCORE_STEP = 0.2

    # 制約
    LR_MIN, LR_MAX = 0.001, 0.1
    TEMP_MIN, TEMP_MAX = 0.3, 3.0
    UP_THRESH_MIN, UP_THRESH_MAX = 0.55, 0.95
    DOWN_THRESH_MIN, DOWN_THRESH_MAX = 0.10, 0.50
    ZSCORE_MIN, ZSCORE_MAX = 1.5, 3.5

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self._meta_history: List[Dict[str, float]] = []
        self._adjustment_log: List[MetaAdjustment] = []
        self._max_history = 200

    # ═══════════════════════════════════════════════════════
    # メタシグナル計算
    # ═══════════════════════════════════════════════════════
    def compute_meta_signals(
        self,
        score_history: List[float],
        alert_count: int = 0,
        policy_entropy: float = 0.5,
        curriculum_changes: int = 0,
    ) -> Dict[str, float]:
        """
        メタ指標を算出:
          - stability: スコアの安定度 (1 - normalized_std)
          - convergence: スコアの改善率 (後半 vs 前半)
          - exploration: 方策エントロピ (正規化)
          - alert_rate: 直近の異常率
          - churn_rate: カリキュラム変更頻度
        """
        signals: Dict[str, float] = {}

        if len(score_history) < 3:
            return {
                "stability": 0.5,
                "convergence": 0.0,
                "exploration": policy_entropy / math.log(3) if policy_entropy > 0 else 0.5,
                "alert_rate": 0.0,
                "churn_rate": 0.0,
            }

        recent = score_history[-self.WINDOW:]

        # 安定性: 1 - (std / mean) — 変動係数の逆
        if len(recent) > 1:
            mean = sum(recent) / len(recent)
            std = statistics.stdev(recent)
            cv = std / max(mean, 0.01)
            signals["stability"] = max(0.0, min(1.0, 1.0 - cv))
        else:
            signals["stability"] = 0.5

        # 収束速度: 後半平均 - 前半平均
        mid = len(recent) // 2
        if mid > 0:
            first_half = sum(recent[:mid]) / mid
            second_half = sum(recent[mid:]) / max(1, len(recent) - mid)
            signals["convergence"] = round(second_half - first_half, 4)
        else:
            signals["convergence"] = 0.0

        # 探索度: エントロピ / log(|A|) (正規化)
        max_entropy = math.log(3)  # 3 actions
        signals["exploration"] = min(1.0, policy_entropy / max_entropy) if max_entropy > 0 else 0.5

        # 異常率: alerts / window_size
        signals["alert_rate"] = min(1.0, alert_count / max(self.WINDOW, 1))

        # チャーン率: カリキュラム変更 / window_size
        signals["churn_rate"] = min(1.0, curriculum_changes / max(self.WINDOW, 1))

        return signals

    # ═══════════════════════════════════════════════════════
    # 自動チューニング
    # ═══════════════════════════════════════════════════════
    def tune(
        self,
        score_history: List[float],
        current_params: Dict[str, float],
        alert_count: int = 0,
        policy_entropy: float = 0.5,
        curriculum_changes: int = 0,
    ) -> MetaReport:
        """
        メタシグナルに基づいてパラメータを自動調整。

        current_params に必要なキー:
          - learning_rate
          - temperature
          - curriculum_up_threshold
          - curriculum_down_threshold
          - anomaly_z_threshold
        """
        signals = self.compute_meta_signals(
            score_history, alert_count, policy_entropy, curriculum_changes,
        )

        adjustments: List[MetaAdjustment] = []
        recommendations: List[str] = []

        lr = current_params.get("learning_rate", 0.01)
        temp = current_params.get("temperature", 1.0)
        up_th = current_params.get("curriculum_up_threshold", 0.75)
        down_th = current_params.get("curriculum_down_threshold", 0.30)
        z_th = current_params.get("anomaly_z_threshold", 2.0)

        # ─── 学習率調整 ───
        # 不安定 → lr を下げる / 収束停滞 → lr を上げる
        if signals["stability"] < 0.4:
            new_lr = max(self.LR_MIN, lr - self.LR_STEP)
            if new_lr != lr:
                adjustments.append(MetaAdjustment(
                    param_name="learning_rate",
                    old_value=lr, new_value=new_lr,
                    reason=f"不安定 (stability={signals['stability']:.2f}) → lr 低下",
                    meta_signal="stability", confidence=0.7,
                ))
                lr = new_lr
        elif signals["convergence"] < -0.05:
            new_lr = min(self.LR_MAX, lr + self.LR_STEP)
            if new_lr != lr:
                adjustments.append(MetaAdjustment(
                    param_name="learning_rate",
                    old_value=lr, new_value=new_lr,
                    reason=f"収束悪化 (convergence={signals['convergence']:.4f}) → lr 増加",
                    meta_signal="convergence", confidence=0.6,
                ))
                lr = new_lr

        # ─── 温度調整 ───
        # 探索不足 → 温度上げる / 探索過多 → 温度下げる
        if signals["exploration"] < 0.3:
            new_temp = min(self.TEMP_MAX, temp + self.TEMP_STEP)
            if new_temp != temp:
                adjustments.append(MetaAdjustment(
                    param_name="temperature",
                    old_value=temp, new_value=new_temp,
                    reason=f"探索不足 (exploration={signals['exploration']:.2f}) → 温度上昇",
                    meta_signal="exploration", confidence=0.65,
                ))
                temp = new_temp
        elif signals["exploration"] > 0.85 and signals["stability"] > 0.7:
            new_temp = max(self.TEMP_MIN, temp - self.TEMP_STEP)
            if new_temp != temp:
                adjustments.append(MetaAdjustment(
                    param_name="temperature",
                    old_value=temp, new_value=new_temp,
                    reason=f"探索過多 & 安定 → 温度低下で活用強化",
                    meta_signal="exploration", confidence=0.6,
                ))
                temp = new_temp

        # ─── カリキュラム閾値 ───
        # チャーンが多い → 閾値を広げる (変更を抑制)
        if signals["churn_rate"] > 0.3:
            new_up = min(self.UP_THRESH_MAX, up_th + self.THRESHOLD_STEP)
            new_down = max(self.DOWN_THRESH_MIN, down_th - self.THRESHOLD_STEP)
            if new_up != up_th or new_down != down_th:
                adjustments.append(MetaAdjustment(
                    param_name="curriculum_up_threshold",
                    old_value=up_th, new_value=new_up,
                    reason=f"チャーン過多 (churn={signals['churn_rate']:.2f}) → 閾値拡大",
                    meta_signal="churn_rate", confidence=0.7,
                ))
                up_th = new_up
                down_th = new_down

        # ─── 異常検知感度 ───
        # アラート過多 → 閾値を緩める / アラートなし & 不安定 → 閾値を厳しく
        if signals["alert_rate"] > 0.4:
            new_z = min(self.ZSCORE_MAX, z_th + self.ZSCORE_STEP)
            if new_z != z_th:
                adjustments.append(MetaAdjustment(
                    param_name="anomaly_z_threshold",
                    old_value=z_th, new_value=new_z,
                    reason=f"アラート過多 (rate={signals['alert_rate']:.2f}) → 感度緩和",
                    meta_signal="alert_rate", confidence=0.6,
                ))
                z_th = new_z
        elif signals["alert_rate"] == 0 and signals["stability"] < 0.5:
            new_z = max(self.ZSCORE_MIN, z_th - self.ZSCORE_STEP)
            if new_z != z_th:
                adjustments.append(MetaAdjustment(
                    param_name="anomaly_z_threshold",
                    old_value=z_th, new_value=new_z,
                    reason=f"不安定なのにアラートなし → 感度強化",
                    meta_signal="alert_rate", confidence=0.5,
                ))
                z_th = new_z

        # ─── 推薦 (調整なしでも出す) ───
        if signals["stability"] > 0.8 and signals["convergence"] > 0.05:
            recommendations.append("パフォーマンス良好 — 現在のパラメータを維持推奨")
        if signals["exploration"] < 0.2:
            recommendations.append("方策が固定化 — 新しいタスクパターンを試す価値あり")
        if signals["convergence"] < -0.1:
            recommendations.append("パフォーマンス悪化傾向 — タスク設計の見直し推奨")
        if len(score_history) < 10:
            recommendations.append("データ不足 — もう少しサイクルを回してから判断推奨")

        # ヘルススコア (0-1)
        health = (
            0.3 * signals["stability"]
            + 0.3 * max(0, min(1, signals["convergence"] + 0.5))
            + 0.2 * (1 - signals["alert_rate"])
            + 0.2 * (1 - signals["churn_rate"])
        )

        # メタ履歴に記録
        self._meta_history.append(signals)
        if len(self._meta_history) > self._max_history:
            self._meta_history = self._meta_history[-self._max_history:]

        # 調整ログ
        self._adjustment_log.extend(adjustments)
        if len(self._adjustment_log) > self._max_history:
            self._adjustment_log = self._adjustment_log[-self._max_history:]

        return MetaReport(
            adjustments=adjustments,
            meta_signals=signals,
            health_score=health,
            recommendations=recommendations,
        )

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """メタコントローラの統計"""
        recent_adjustments = self._adjustment_log[-10:]
        param_changes: Dict[str, int] = {}
        for adj in self._adjustment_log:
            param_changes[adj.param_name] = param_changes.get(adj.param_name, 0) + 1

        # 最新のメタシグナル
        latest_signals = self._meta_history[-1] if self._meta_history else {}

        return {
            "total_adjustments": len(self._adjustment_log),
            "param_change_counts": param_changes,
            "meta_history_len": len(self._meta_history),
            "latest_signals": {k: round(v, 4) for k, v in latest_signals.items()},
            "recent_adjustments": [a.to_dict() for a in recent_adjustments],
        }

    def get_health_trend(self, window: int = 10) -> List[float]:
        """ヘルススコアのトレンド"""
        if not self._meta_history:
            return []
        trend = []
        for signals in self._meta_history[-window:]:
            h = (
                0.3 * signals.get("stability", 0.5)
                + 0.3 * max(0, min(1, signals.get("convergence", 0) + 0.5))
                + 0.2 * (1 - signals.get("alert_rate", 0))
                + 0.2 * (1 - signals.get("churn_rate", 0))
            )
            trend.append(round(h, 4))
        return trend
