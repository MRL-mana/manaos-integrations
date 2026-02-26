#!/usr/bin/env python3
"""
Distributional Reward — 報酬分布トラッキング + リスク感応意思決定
================================================================
報酬の"期待値"だけでなく、分布全体（分位数）を追跡し、
CVaR / VaR 等のリスク指標を元に慎重な or 積極的な方策を取る。

Princeton RL-Anything Round 10 Module 2.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════
# 定数
# ═══════════════════════════════════════════════════════
MAX_SAMPLES = 2000
DEFAULT_QUANTILES = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
RISK_ALPHA = 0.1  # CVaR α — 下位10%の条件付き期待値
RISK_NEUTRAL_THRESHOLD = 0.5  # リスク中立のCVaR閾値


# ═══════════════════════════════════════════════════════
# データクラス
# ═══════════════════════════════════════════════════════
@dataclass
class RewardDistribution:
    """ある状態-行動ペアの報酬分布"""
    key: str
    samples: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    quantiles: Dict[str, float] = field(default_factory=dict)
    var_at_alpha: float = 0.0   # Value-at-Risk (下位α分位)
    cvar_at_alpha: float = 0.0  # Conditional VaR (下位α%の平均)
    skewness: float = 0.0
    count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("samples", None)  # サンプル生データは除外
        return d


@dataclass
class RiskProfile:
    """全体のリスクプロファイル"""
    overall_cvar: float = 0.0
    overall_var: float = 0.0
    risk_level: str = "neutral"  # conservative / neutral / aggressive
    recommendation: str = ""
    tail_risk_ratio: float = 0.0  # 下位10%のサンプル割合
    distribution_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskAdjustedScore:
    """リスク調整済みスコア"""
    raw_score: float
    risk_adjusted: float
    risk_penalty: float
    cvar: float
    var: float
    confidence_interval: Tuple[float, float] = (0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_score": self.raw_score,
            "risk_adjusted": round(self.risk_adjusted, 4),
            "risk_penalty": round(self.risk_penalty, 4),
            "cvar": round(self.cvar, 4),
            "var": round(self.var, 4),
            "confidence_interval": [round(v, 4) for v in self.confidence_interval],
        }


# ═══════════════════════════════════════════════════════
# メインクラス
# ═══════════════════════════════════════════════════════
class DistributionalReward:
    """
    報酬の分布全体を追跡し、リスク感応な意思決定を支援。
    - 状態-行動ペアごとに報酬分布を維持
    - VaR / CVaR でリスク評価
    - リスク調整済みスコアを算出
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        alpha: float = RISK_ALPHA,
        quantiles: Optional[List[float]] = None,
    ):
        self._persist_path = persist_path
        self._alpha = alpha
        self._quantiles = quantiles or DEFAULT_QUANTILES

        # key → samples
        self._distributions: Dict[str, List[float]] = defaultdict(list)
        self._total_samples = 0
        self._all_rewards: List[float] = []  # global reward history
        self._risk_checks = 0

        self._restore()

    # ═══════════════════════════════════════════════════════
    # 報酬記録
    # ═══════════════════════════════════════════════════════
    def record(self, key: str, reward: float) -> RewardDistribution:
        """
        報酬サンプルを記録し、分布統計を再計算。
        key は "state|action" 等の任意のカテゴリ。
        """
        self._distributions[key].append(reward)
        if len(self._distributions[key]) > MAX_SAMPLES:
            self._distributions[key] = self._distributions[key][-MAX_SAMPLES:]

        self._all_rewards.append(reward)
        if len(self._all_rewards) > MAX_SAMPLES * 5:
            self._all_rewards = self._all_rewards[-(MAX_SAMPLES * 5):]

        self._total_samples += 1
        dist = self._compute_distribution(key)
        self._persist()
        return dist

    def record_batch(self, key: str, rewards: List[float]) -> RewardDistribution:
        """複数報酬を一括記録"""
        for r in rewards:
            self._distributions[key].append(r)
            self._all_rewards.append(r)
            self._total_samples += 1
        if len(self._distributions[key]) > MAX_SAMPLES:
            self._distributions[key] = self._distributions[key][-MAX_SAMPLES:]
        if len(self._all_rewards) > MAX_SAMPLES * 5:
            self._all_rewards = self._all_rewards[-(MAX_SAMPLES * 5):]
        dist = self._compute_distribution(key)
        self._persist()
        return dist

    # ═══════════════════════════════════════════════════════
    # 分布計算
    # ═══════════════════════════════════════════════════════
    def _compute_distribution(self, key: str) -> RewardDistribution:
        """指定キーの報酬分布統計を計算"""
        samples = self._distributions.get(key, [])
        if not samples:
            return RewardDistribution(key=key)

        sorted_s = sorted(samples)
        n = len(sorted_s)
        mean = statistics.mean(sorted_s)
        std = statistics.stdev(sorted_s) if n >= 2 else 0.0
        min_val = sorted_s[0]
        max_val = sorted_s[-1]

        # 分位数
        qs = {}
        for q in self._quantiles:
            idx = int(q * (n - 1))
            qs[f"q{int(q*100):03d}"] = round(sorted_s[idx], 4)

        # VaR at alpha
        var_idx = max(0, int(self._alpha * n) - 1)
        var_val = sorted_s[var_idx]

        # CVaR at alpha (下位alpha%の条件付き期待値)
        cvar_samples = sorted_s[:max(1, int(self._alpha * n))]
        cvar_val = statistics.mean(cvar_samples) if cvar_samples else 0.0

        # Skewness (歪度)
        skew = 0.0
        if n >= 3 and std > 0:
            skew = sum((x - mean) ** 3 for x in sorted_s) / (n * std ** 3)

        return RewardDistribution(
            key=key,
            mean=round(mean, 4),
            std=round(std, 4),
            min_val=round(min_val, 4),
            max_val=round(max_val, 4),
            quantiles=qs,
            var_at_alpha=round(var_val, 4),
            cvar_at_alpha=round(cvar_val, 4),
            skewness=round(skew, 4),
            count=n,
        )

    def get_distribution(self, key: str) -> RewardDistribution:
        """指定キーの分布を取得"""
        return self._compute_distribution(key)

    def get_all_distributions(self) -> Dict[str, Dict[str, Any]]:
        """全分布を取得"""
        return {k: self._compute_distribution(k).to_dict() for k in self._distributions}

    # ═══════════════════════════════════════════════════════
    # リスク評価
    # ═══════════════════════════════════════════════════════
    def risk_adjust(self, raw_score: float, key: Optional[str] = None, risk_aversion: float = 0.3) -> RiskAdjustedScore:
        """
        リスク調整済みスコアを算出。
        risk_aversion: 0=リスク中立, 1=最大リスク回避
        """
        self._risk_checks += 1

        # キー指定があればそのCVaRを使用、なければ全体
        if key and key in self._distributions:
            dist = self._compute_distribution(key)
            cvar = dist.cvar_at_alpha
            var = dist.var_at_alpha
            std = dist.std
        else:
            # 全体分布から算出
            if self._all_rewards:
                sorted_all = sorted(self._all_rewards)
                n = len(sorted_all)
                cvar_idx = max(1, int(self._alpha * n))
                cvar = statistics.mean(sorted_all[:cvar_idx]) if sorted_all[:cvar_idx] else 0.5
                var_idx = max(0, int(self._alpha * n) - 1)
                var = sorted_all[var_idx]
                std = statistics.stdev(sorted_all) if n >= 2 else 0.0
            else:
                cvar = 0.5
                var = 0.0
                std = 0.0

        # リスクペナルティ = risk_aversion × (mean - CVaR) / max(std, 0.01)
        if std > 0.01:
            tail_gap = raw_score - cvar
            risk_penalty = risk_aversion * max(0, tail_gap) * (std / (std + 0.1))
        else:
            risk_penalty = 0.0

        risk_adjusted = raw_score - risk_penalty

        # 信頼区間 (± 1.96σ/√n)
        n_all = len(self._all_rewards) if self._all_rewards else 1
        margin = 1.96 * std / math.sqrt(max(1, n_all))
        ci = (round(max(0, raw_score - margin), 4), round(min(1, raw_score + margin), 4))

        return RiskAdjustedScore(
            raw_score=raw_score,
            risk_adjusted=round(max(0, min(1, risk_adjusted)), 4),
            risk_penalty=round(risk_penalty, 4),
            cvar=round(cvar, 4),
            var=round(var, 4),
            confidence_interval=ci,
        )

    def get_risk_profile(self) -> RiskProfile:
        """全体のリスクプロファイル"""
        if not self._all_rewards:
            return RiskProfile(recommendation="データ不足。サイクルを実行してください。")

        sorted_all = sorted(self._all_rewards)
        n = len(sorted_all)

        # 全体CVaR / VaR
        cvar_idx = max(1, int(self._alpha * n))
        overall_cvar = statistics.mean(sorted_all[:cvar_idx])
        var_idx = max(0, int(self._alpha * n) - 1)
        overall_var = sorted_all[var_idx]

        # テールリスク比率 (下位10%のうち、0.3未満の割合)
        tail_samples = sorted_all[:max(1, int(0.1 * n))]
        tail_risk_ratio = sum(1 for s in tail_samples if s < 0.3) / max(1, len(tail_samples))

        # リスクレベル判定
        if overall_cvar < 0.2:
            risk_level = "high_risk"
            recommendation = "CVaR が低い: 難易度を下げるか、より安全な行動を推奨"
        elif overall_cvar < RISK_NEUTRAL_THRESHOLD:
            risk_level = "moderate_risk"
            recommendation = "中程度のリスク: 継続監視しつつ、探索を慎重に"
        else:
            risk_level = "low_risk"
            recommendation = "リスク許容範囲内: 積極的な探索が可能"

        return RiskProfile(
            overall_cvar=round(overall_cvar, 4),
            overall_var=round(overall_var, 4),
            risk_level=risk_level,
            recommendation=recommendation,
            tail_risk_ratio=round(tail_risk_ratio, 4),
            distribution_count=len(self._distributions),
        )

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """全体統計"""
        profile = self.get_risk_profile()
        global_dist = None
        if self._all_rewards:
            sorted_all = sorted(self._all_rewards)
            global_dist = {
                "mean": round(statistics.mean(sorted_all), 4),
                "std": round(statistics.stdev(sorted_all), 4) if len(sorted_all) >= 2 else 0.0,
                "min": round(sorted_all[0], 4),
                "max": round(sorted_all[-1], 4),
                "count": len(sorted_all),
            }

        return {
            "total_samples": self._total_samples,
            "distribution_count": len(self._distributions),
            "risk_checks": self._risk_checks,
            "risk_profile": profile.to_dict(),
            "global_distribution": global_dist,
            "alpha": self._alpha,
        }

    def get_quantile_summary(self) -> Dict[str, Any]:
        """全分布の分位数サマリー"""
        summaries = {}
        for key in self._distributions:
            dist = self._compute_distribution(key)
            summaries[key] = {
                "count": dist.count,
                "mean": dist.mean,
                "std": dist.std,
                "cvar": dist.cvar_at_alpha,
                "var": dist.var_at_alpha,
                "quantiles": dist.quantiles,
            }
        return summaries

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "distributions": {k: v[-MAX_SAMPLES:] for k, v in self._distributions.items()},
                "all_rewards": self._all_rewards[-(MAX_SAMPLES * 5):],
                "total_samples": self._total_samples,
                "risk_checks": self._risk_checks,
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
            for k, v in data.get("distributions", {}).items():
                self._distributions[k] = v
            self._all_rewards = data.get("all_rewards", [])
            self._total_samples = data.get("total_samples", 0)
            self._risk_checks = data.get("risk_checks", 0)
        except Exception:
            pass
