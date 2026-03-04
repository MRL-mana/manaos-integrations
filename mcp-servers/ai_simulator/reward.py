"""
Reward Engine: 成果を数値化（重み付き合成）
R = w1*成功率 + w2*速度改善 + w3*エラー低減 + w4*人間FB + w5*再現性 + w6*コスト効率
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

POLICY_FILE = Path(os.getenv("AISIM_EVOLUTION_POLICY", "/root/ai_simulator/config/evolution_policy.yaml"))

def load_policy() -> Dict[str, Any]:
    """ポリシーファイルを読み込む"""
    if POLICY_FILE.exists():
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    logger.warning(f"Policy file not found: {POLICY_FILE}. Using defaults.")
    return {
        "reward_weights": {
            "success_rate": 0.35,
            "latency_gain": 0.20,
            "error_drop": 0.20,
            "human_feedback": 0.10,
            "reproducibility": 0.10,
            "cost_efficiency": 0.05,
        }
    }

def compute_reward(
    baseline_metrics: Dict[str, Any],
    trial_metrics: Dict[str, Any],
    human_feedback: Optional[float] = None,
    repro_score: Optional[float] = None,
    combo_multiplier: float = 1.0
) -> float:
    """
    リワードを計算
    :param baseline_metrics: ベースライン指標
    :param trial_metrics: トライアル指標
    :param human_feedback: 人間フィードバック（+1/0/-1）
    :param repro_score: 再現性スコア（0-1）
    :param combo_multiplier: コンボ倍率（デフォルト1.0）
    :return: リワード値（0-1）
    """
    policy = load_policy()
    weights_raw = policy["reward_weights"]

    # 重みの正規化（総和が1になるように）
    total_weight = sum(weights_raw.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights_raw.items()}
    else:
        # フォールバック: 均等重み
        weights = {k: 1.0 / len(weights_raw) for k in weights_raw.keys()}

    # 1. 成功率
    success_rate_reward = trial_metrics.get("success_rate", 0.0)

    # 2. 速度改善 = max(0, (baseline_p95 − trial_p95) / baseline_p95)
    baseline_p95 = baseline_metrics.get("p95_ms", 1000)
    trial_p95 = trial_metrics.get("p95_ms", baseline_p95)
    if baseline_p95 > 0:
        latency_gain = max(0.0, (baseline_p95 - trial_p95) / baseline_p95)
    else:
        # ゼロ割対策: 小さなεで割る
        epsilon = 1.0
        latency_gain = max(0.0, (baseline_p95 - trial_p95) / epsilon) if (baseline_p95 - trial_p95) > 0 else 0.0

    # 3. エラー低減 = max(0, (baseline_err − trial_err) / baseline_err)
    baseline_err = baseline_metrics.get("error_rate", 0.05)
    trial_err = trial_metrics.get("error_rate", baseline_err)
    if baseline_err > 0:
        error_drop = max(0.0, (baseline_err - trial_err) / baseline_err)
    else:
        # ゼロ割対策: 小さなεで割る
        epsilon = 0.001
        error_drop = max(0.0, (baseline_err - trial_err) / epsilon) if (baseline_err - trial_err) > 0 else 0.0

    # 4. 人間フィードバック（+1/0/-1 を 0-1に正規化）
    if human_feedback is not None:
        human_fb_score = (human_feedback + 1.0) / 2.0  # -1→0, 0→0.5, +1→1
    else:
        human_fb_score = 0.5  # デフォルト（中立）

    # 5. 再現性（分散ペナルティ）
    if repro_score is not None:
        repro_score_normalized = repro_score  # 既に0-1で提供されている想定
    else:
        repro_score_normalized = 1.0  # デフォルト（完璧な再現性）

    # 6. コスト効率 = （成功1件あたりの実コスト）逆数を正規化
    baseline_cost = baseline_metrics.get("cost_per_success", 6.5)
    trial_cost = trial_metrics.get("cost_per_success", baseline_cost)
    if baseline_cost > 0 and trial_cost > 0:
        cost_efficiency = min(1.0, baseline_cost / trial_cost)  # ベースラインより安い→1.0に近づく
    else:
        cost_efficiency = 0.5

    # 重み付き合成
    reward = (
        weights["success_rate"] * success_rate_reward +
        weights["latency_gain"] * latency_gain +
        weights["error_drop"] * error_drop +
        weights["human_feedback"] * human_fb_score +
        weights["reproducibility"] * repro_score_normalized +
        weights["cost_efficiency"] * cost_efficiency
    )

    # コンボ倍率適用（最大10回で1.2倍）
    reward = reward * combo_multiplier

    # 0-1にクランプ
    reward = max(0.0, min(1.0, reward))

    logger.debug(
        f"Reward computed: {reward:.3f} "
        f"(success={success_rate_reward:.3f}, latency={latency_gain:.3f}, "
        f"error={error_drop:.3f}, human={human_fb_score:.3f}, "
        f"repro={repro_score_normalized:.3f}, cost={cost_efficiency:.3f})"
    )

    return reward
