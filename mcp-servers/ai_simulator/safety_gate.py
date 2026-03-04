"""
Safety Gate: 信頼度・SLO・コストで即時ストップ
"""

import yaml
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

POLICY_FILE = Path(os.getenv("AISIM_EVOLUTION_POLICY", "/root/ai_simulator/config/evolution_policy.yaml"))

def load_policy() -> Dict[str, Any]:
    """ポリシーファイルを読み込む"""
    if POLICY_FILE.exists():
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

def check_safety_gate(
    metrics: Dict[str, Any],
    confidence_history: Optional[List[float]] = None
) -> Tuple[bool, Optional[str]]:
    """
    セーフティゲートチェック
    :param metrics: メトリクス（p95_ms, confidence, cost_per_success等）
    :param confidence_history: 信頼度履歴（連続低信頼度チェック用）
    :return: (safe, reason) - safe=Trueなら安全、Falseなら停止が必要
    """
    policy = load_policy()
    constraints = policy.get("constraints", {})
    rollback = policy.get("rollback_triggers", {})
    
    # 1. p95 > hard_slo チェック
    hard_slo = constraints.get("hard_slo_p95_ms", 3000)
    p95 = metrics.get("p95_ms", 0)
    if p95 > hard_slo:
        return False, f"p95 {p95}ms exceeds hard SLO {hard_slo}ms"
    
    # 2. confidence < threshold チェック
    confidence_threshold = rollback.get("confidence_dropped", 0.70)
    confidence = metrics.get("confidence", 1.0)
    if confidence < confidence_threshold:
        return False, f"confidence {confidence:.2f} below threshold {confidence_threshold}"
    
    # 3. cost/success > max_cost チェック
    max_cost = constraints.get("max_cost_per_success_jpy", 10)
    cost = metrics.get("cost_per_success", 0)
    if cost > max_cost:
        return False, f"cost {cost}JPY per success exceeds max {max_cost}JPY"
    
    # 4. 連続低信頼度チェック
    if confidence_history:
        consecutive_threshold = rollback.get("consecutive_low_confidence", 3)
        low_confidence_threshold = 0.85
        consecutive_low = sum(1 for c in confidence_history[-consecutive_threshold:] if c < low_confidence_threshold)
        if consecutive_low >= consecutive_threshold:
            return False, f"confidence below {low_confidence_threshold} for {consecutive_low} consecutive times"
    
    # 全て通過
    return True, None

def should_rollback(
    variant_metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    promote_threshold_delta: float = 0.05
) -> Tuple[bool, Optional[str]]:
    """
    ロールバックが必要か判定
    :param variant_metrics: バリアントメトリクス
    :param baseline_metrics: ベースラインメトリクス
    :param promote_threshold_delta: 昇格閾値（デフォルト+5%）
    :return: (should_rollback, reason)
    """
    # セーフティゲートチェック
    safe, reason = check_safety_gate(variant_metrics)
    if not safe:
        return True, reason
    
    # ベースラインより悪化した場合もロールバック検討
    baseline_reward = baseline_metrics.get("reward", 0.7)  # 仮定
    variant_reward = variant_metrics.get("reward", 0.0)
    
    if variant_reward < baseline_reward - promote_threshold_delta:
        return True, f"reward {variant_reward:.3f} below baseline {baseline_reward:.3f} by more than {promote_threshold_delta}"
    
    return False, None
