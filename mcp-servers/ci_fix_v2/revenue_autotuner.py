"""
Revenue Auto-Tuner — 収益駆動パラメータ自動調整
================================================================
収益トレンド × RLAnything MetaController を接続し、
収益信号に基づいて RL パラメータを自動チューニングする。

完全閉ループ:
  revenue_tracker.db → revenue_anomaly.py (異常検知)
                     → revenue_autotuner.py (自動調整)  ← THIS
                     → MetaController.tune()
                     → PolicyGradient / RewardShaper / Curriculum 更新
                     → 品質向上 → 収益向上 → ...

調整戦略:
  1) 収益下降トレンド → 探索を増やす (temperature ↑, lr ↑)
  2) 収益上昇トレンド → 活用を強化  (temperature ↓, lr 微減)
  3) 収益停滞 (plateau) → 大幅に探索 (lr ↑, anomaly_z ↓)
  4) 異常スパイク → 安定化 (lr ↓, temperature 微減)
  5) 正常安定 → 現状維持

判断指標:
  - revenue_trend.direction: rising / falling / stable
  - revenue_trend.change_pct: 変化率%
  - anomaly_alert_count: 異常数
  - loop_health.score: 0-100 ジェルスコア
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

_log = logging.getLogger("manaos.revenue_autotuner")


# ─── データクラス ────────────────────────────────────

@dataclass
class TuneAction:
    """1 回の自動チューニングアクション"""
    param: str
    old_value: float
    new_value: float
    reason: str
    strategy: str          # "explore", "exploit", "stabilize", "maintain"
    confidence: float      # 0-1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TuneReport:
    """チューニングレポート"""
    strategy: str          # 最終戦略名
    actions: List[TuneAction]
    revenue_signal: Dict[str, Any]
    rl_signal: Dict[str, Any]
    health_score: float    # 調整後の推定健全度
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "actions": [a.to_dict() for a in self.actions],
            "action_count": len(self.actions),
            "revenue_signal": self.revenue_signal,
            "rl_signal": self.rl_signal,
            "health_score": round(self.health_score, 2),
            "timestamp": self.timestamp,
        }


# ─── 戦略定数 ────────────────────────────────────────

# 変化率の閾値 (%)
_RISING_THRESHOLD = 10.0
_FALLING_THRESHOLD = -10.0
_PLATEAU_THRESHOLD = 2.0     # |change| < 2% かつ alert_count > 0

# パラメータ調整ステップ
_LR_STEP = 0.003
_TEMP_STEP = 0.15
_Z_STEP = 0.25

# 制約
_LR_RANGE = (0.001, 0.1)
_TEMP_RANGE = (0.3, 3.0)
_Z_RANGE = (1.2, 3.5)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


# ─── メイン関数 ──────────────────────────────────────

def compute_tune_strategy(
    revenue_trend: Dict[str, Any],
    anomaly_alerts: List[Dict[str, Any]],
    loop_health_score: float,
) -> str:
    """
    収益シグナルから最適な調整戦略を決定。

    Returns:
        "explore" | "exploit" | "stabilize" | "plateau_break" | "maintain"
    """
    direction = revenue_trend.get("direction", "unknown")
    change_pct = revenue_trend.get("change_pct", 0)
    alert_count = len(anomaly_alerts)

    # 1) 異常スパイク (アラート多数 + 上昇) → 安定化
    if alert_count >= 3 and change_pct > _RISING_THRESHOLD:
        return "stabilize"

    # 2) 下降トレンド → 探索強化
    if direction == "falling" or change_pct < _FALLING_THRESHOLD:
        return "explore"

    # 3) 停滞 (変化小 + アラートあり or 低ヘルス) → plateau_break
    if abs(change_pct) < _PLATEAU_THRESHOLD and (alert_count > 0 or loop_health_score < 30):
        return "plateau_break"

    # 4) 上昇トレンド → 活用強化
    if direction == "rising" or change_pct > _RISING_THRESHOLD:
        return "exploit"

    # 5) それ以外 → 現状維持
    return "maintain"


def auto_tune(
    revenue_trend: Dict[str, Any],
    anomaly_alerts: List[Dict[str, Any]],
    loop_health_score: float,
    current_rl_params: Optional[Dict[str, float]] = None,
) -> TuneReport:
    """
    収益信号に基づいて RL パラメータを自動調整。

    Args:
        revenue_trend: {"direction": "rising"/"falling"/"stable", "change_pct": float}
        anomaly_alerts: AnomalyDetector のアラートリスト
        loop_health_score: 0-100 のループ健全性スコア
        current_rl_params: 現在のRLパラメータ (省略時デフォルト)

    Returns:
        TuneReport — 戦略 + 実行アクション + 推定健全度
    """
    params = current_rl_params or {}
    lr = params.get("learning_rate", 0.01)
    temp = params.get("temperature", 1.0)
    z_th = params.get("anomaly_z_threshold", 2.0)
    up_th = params.get("curriculum_up_threshold", 0.75)
    down_th = params.get("curriculum_down_threshold", 0.30)

    strategy = compute_tune_strategy(revenue_trend, anomaly_alerts, loop_health_score)
    actions: List[TuneAction] = []
    change_pct = revenue_trend.get("change_pct", 0)
    alert_count = len(anomaly_alerts)

    if strategy == "explore":
        # 収益下降 → 品質改善のため探索を増やす
        new_lr = _clamp(lr + _LR_STEP, *_LR_RANGE)
        new_temp = _clamp(temp + _TEMP_STEP, *_TEMP_RANGE)
        if new_lr != lr:
            actions.append(TuneAction(
                param="learning_rate", old_value=lr, new_value=new_lr,
                reason=f"収益下降 ({change_pct:+.1f}%) → 学習率を上げて新パターンを探索",
                strategy="explore", confidence=0.7,
            ))
        if new_temp != temp:
            actions.append(TuneAction(
                param="temperature", old_value=temp, new_value=new_temp,
                reason=f"収益下降 → 温度を上げてアクション多様性を増加",
                strategy="explore", confidence=0.65,
            ))

    elif strategy == "exploit":
        # 収益上昇 → 現在の方向性を強化
        new_lr = _clamp(lr - _LR_STEP * 0.5, *_LR_RANGE)
        new_temp = _clamp(temp - _TEMP_STEP * 0.5, *_TEMP_RANGE)
        if new_lr != lr:
            actions.append(TuneAction(
                param="learning_rate", old_value=lr, new_value=new_lr,
                reason=f"収益上昇 ({change_pct:+.1f}%) → 学習率微減で安定活用",
                strategy="exploit", confidence=0.6,
            ))
        if new_temp != temp:
            actions.append(TuneAction(
                param="temperature", old_value=temp, new_value=new_temp,
                reason=f"収益上昇 → 温度微減でトップアクション確信度を強化",
                strategy="exploit", confidence=0.55,
            ))

    elif strategy == "plateau_break":
        # 停滞 → 大幅に探索 + 異常検知感度を上げる
        new_lr = _clamp(lr + _LR_STEP * 1.5, *_LR_RANGE)
        new_temp = _clamp(temp + _TEMP_STEP * 1.5, *_TEMP_RANGE)
        new_z = _clamp(z_th - _Z_STEP, *_Z_RANGE)
        if new_lr != lr:
            actions.append(TuneAction(
                param="learning_rate", old_value=lr, new_value=new_lr,
                reason=f"収益停滞 (変化率 {change_pct:+.1f}%) → 学習率大幅UP",
                strategy="plateau_break", confidence=0.75,
            ))
        if new_temp != temp:
            actions.append(TuneAction(
                param="temperature", old_value=temp, new_value=new_temp,
                reason=f"収益停滞 → 温度大幅UP で脱停滞",
                strategy="plateau_break", confidence=0.7,
            ))
        if new_z != z_th:
            actions.append(TuneAction(
                param="anomaly_z_threshold", old_value=z_th, new_value=new_z,
                reason=f"停滞状態 → 異常検知感度UP (Z閾値 {z_th:.1f}→{new_z:.1f})",
                strategy="plateau_break", confidence=0.6,
            ))

    elif strategy == "stabilize":
        # 異常スパイク → 安定化
        new_lr = _clamp(lr - _LR_STEP, *_LR_RANGE)
        new_temp = _clamp(temp - _TEMP_STEP, *_TEMP_RANGE)
        new_z = _clamp(z_th + _Z_STEP, *_Z_RANGE)
        if new_lr != lr:
            actions.append(TuneAction(
                param="learning_rate", old_value=lr, new_value=new_lr,
                reason=f"異常スパイク ({alert_count}件) → 学習率を下げて安定化",
                strategy="stabilize", confidence=0.8,
            ))
        if new_temp != temp:
            actions.append(TuneAction(
                param="temperature", old_value=temp, new_value=new_temp,
                reason=f"異常スパイク → 温度低下で保守的に",
                strategy="stabilize", confidence=0.7,
            ))
        if new_z != z_th:
            actions.append(TuneAction(
                param="anomaly_z_threshold", old_value=z_th, new_value=new_z,
                reason=f"異常多発 → Z閾値を緩めてノイズ耐性UP",
                strategy="stabilize", confidence=0.65,
            ))

    # "maintain" → アクションなし

    # 推定健全度 (調整後)
    estimated_health = _estimate_post_tune_health(
        loop_health_score, strategy, len(actions),
    )

    # RL シグナル (現在のパラメータ + 調整)
    rl_signal = {k: round(v, 4) for k, v in params.items()} if params else {}
    for a in actions:
        rl_signal[f"{a.param}_adjusted"] = round(a.new_value, 4)

    _log.info(
        "auto_tune: strategy=%s actions=%d health=%.1f→%.1f change=%.1f%%",
        strategy, len(actions), loop_health_score, estimated_health, change_pct,
    )

    return TuneReport(
        strategy=strategy,
        actions=actions,
        revenue_signal={
            "direction": revenue_trend.get("direction", "unknown"),
            "change_pct": revenue_trend.get("change_pct", 0),
            "anomaly_count": alert_count,
        },
        rl_signal=rl_signal,
        health_score=estimated_health,
    )


def _estimate_post_tune_health(
    current_health: float,
    strategy: str,
    action_count: int,
) -> float:
    """調整後の推定健全度 (楽観的バイアス)"""
    if strategy == "maintain":
        return current_health

    # 調整 1 アクションにつき +2〜5 ポイントの期待改善
    boost_per_action = {
        "explore": 3.0,
        "exploit": 2.0,
        "plateau_break": 5.0,
        "stabilize": 4.0,
    }
    boost = boost_per_action.get(strategy, 2.0) * action_count
    return min(100.0, current_health + boost)


# ─── 適用ヘルパー ────────────────────────────────────

def apply_tune_to_orchestrator(report: TuneReport) -> Dict[str, Any]:
    """
    TuneReport のアクションを RLAnything Orchestrator に適用。

    Returns:
        {"applied": int, "skipped": int, "details": [...]}
    """
    try:
        from image_generation_service.rl_bridge import _get_orchestrator
        rl = _get_orchestrator()
    except Exception:
        rl = None

    if rl is None:
        return {"applied": 0, "skipped": len(report.actions),
                "error": "RLAnything orchestrator not available"}

    applied = []
    skipped = []
    for action in report.actions:
        try:
            if action.param == "learning_rate":
                rl.policy_gradient.lr = action.new_value
            elif action.param == "temperature":
                rl.policy_gradient.temperature = action.new_value
            elif action.param == "anomaly_z_threshold":
                if hasattr(rl.anomaly_detector, 'z_threshold'):
                    rl.anomaly_detector.z_threshold = action.new_value
            elif action.param == "curriculum_up_threshold":
                if hasattr(rl.curriculum, 'up_threshold'):
                    rl.curriculum.up_threshold = action.new_value
            elif action.param == "curriculum_down_threshold":
                if hasattr(rl.curriculum, 'down_threshold'):
                    rl.curriculum.down_threshold = action.new_value
            else:
                skipped.append({"param": action.param, "reason": "unknown_param"})
                continue
            applied.append({
                "param": action.param,
                "old": round(action.old_value, 4),
                "new": round(action.new_value, 4),
            })
            _log.info("Applied: %s %.4f → %.4f", action.param, action.old_value, action.new_value)
        except Exception as e:
            skipped.append({"param": action.param, "reason": str(e)})
            _log.warning("Skip: %s → %s", action.param, e)

    return {
        "applied": len(applied),
        "skipped": len(skipped),
        "details": applied,
        "skipped_details": skipped,
    }
