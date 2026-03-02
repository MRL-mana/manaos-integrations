#!/usr/bin/env python3
"""
AdversarialRobustness — 敵対的摂動テスト & ロバスト方策評価
==========================================================
Round 11 モジュール (2/3)

方策の頑健性をテスト・評価するモジュール。敵対的な入力摂動を生成し、
方策がどの程度安定した判断を維持できるかを計測する。

主な機能:
  - ε-ball ベースの状態摂動生成
  - 摂動下での方策安定性テスト
  - ロバストネススコア算出
  - 脆弱状態の特定と記録
  - 耐障害性レポート生成
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── 定数 ──

MAX_TESTS = 3000
DEFAULT_EPSILON = 0.1       # 摂動半径
DEFAULT_N_PERTURBATIONS = 10  # 1状態あたりの摂動数
VULNERABILITY_THRESHOLD = 0.3  # 安定性がこれ未満なら脆弱
ROBUSTNESS_HISTORY_SIZE = 500


# ── データ型 ──

@dataclass
class PerturbationResult:
    """単一摂動テスト結果"""
    original_state: str
    epsilon: float
    n_perturbations: int
    original_action: str
    stability: float         # 同じアクションが選ばれた割合
    worst_deviation: float   # 最大スコア偏差
    mean_deviation: float    # 平均スコア偏差

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RobustnessReport:
    """ロバストネス分析レポート"""
    overall_robustness: float
    tests_conducted: int
    vulnerable_states: int
    stable_states: int
    avg_stability: float
    worst_stability: float
    mean_deviation: float
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VulnerableState:
    """脆弱と判定された状態"""
    state_id: str
    stability: float
    worst_deviation: float
    last_tested: float
    test_count: int


# ── メインクラス ──

class AdversarialRobustness:
    """敵対的ロバストネス評価エンジン"""

    def __init__(self, *, persist_path: Optional[Path] = None,
                 config: Optional[Dict] = None):
        self._test_results: List[PerturbationResult] = []
        self._vulnerable_states: Dict[str, VulnerableState] = {}
        self._robustness_history: List[Dict[str, Any]] = []

        # action→score マッピング（シミュレーション用）
        self._action_scores: Dict[str, List[float]] = defaultdict(list)

        self._persist = persist_path
        cfg = config or {}
        self._epsilon = cfg.get("adversarial_epsilon", DEFAULT_EPSILON)
        self._n_perturbations = cfg.get("adversarial_n_perturbations", DEFAULT_N_PERTURBATIONS)
        self._vuln_threshold = cfg.get("adversarial_vuln_threshold", VULNERABILITY_THRESHOLD)

        self._restore()

    # ── 摂動テスト ──

    def test_robustness(self, state_id: str, action: str,
                        score: float, *,
                        epsilon: Optional[float] = None,
                        n_perturbations: Optional[int] = None) -> PerturbationResult:
        """
        指定状態に対する摂動テストを実行。
        action/score ペアに対し、ε-ball 内の摂動でどの程度結果が変わるかを評価。
        """
        eps = epsilon or self._epsilon
        n_pert = n_perturbations or self._n_perturbations

        # アクション履歴に記録
        self._action_scores[action].append(score)

        # 摂動生成 & テスト
        deviations = []
        action_matches = 0

        for _ in range(n_pert):
            # スコアに摂動を加える
            perturbation = random.gauss(0, eps)
            perturbed_score = max(0.0, min(1.0, score + perturbation))
            deviation = abs(perturbed_score - score)
            deviations.append(deviation)

            # 摂動後も同じアクションが最善か判定
            # （スコアの変化が小さければ同じアクション）
            if deviation < eps * 0.5:
                action_matches += 1

        stability = action_matches / n_pert if n_pert > 0 else 1.0
        worst_dev = max(deviations) if deviations else 0.0
        mean_dev = sum(deviations) / len(deviations) if deviations else 0.0

        result = PerturbationResult(
            original_state=state_id,
            epsilon=eps,
            n_perturbations=n_pert,
            original_action=action,
            stability=round(stability, 4),
            worst_deviation=round(worst_dev, 4),
            mean_deviation=round(mean_dev, 4),
        )
        self._test_results.append(result)

        # 脆弱状態チェック
        if stability < self._vuln_threshold:
            self._vulnerable_states[state_id] = VulnerableState(
                state_id=state_id,
                stability=stability,
                worst_deviation=worst_dev,
                last_tested=time.time(),
                test_count=self._vulnerable_states.get(state_id, VulnerableState(
                    state_id, 0, 0, 0, 0)).test_count + 1,
            )

        # 容量制限
        if len(self._test_results) > MAX_TESTS:
            self._test_results = self._test_results[-MAX_TESTS:]

        self._persist_state()
        return result

    # ── ロバストネスレポート ──

    def generate_report(self) -> RobustnessReport:
        """全体ロバストネスレポートを生成"""
        if not self._test_results:
            return RobustnessReport(
                overall_robustness=1.0, tests_conducted=0,
                vulnerable_states=0, stable_states=0,
                avg_stability=1.0, worst_stability=1.0,
                mean_deviation=0.0, timestamp=time.time(),
            )

        stabilities = [r.stability for r in self._test_results]
        deviations = [r.mean_deviation for r in self._test_results]

        avg_stab = sum(stabilities) / len(stabilities)
        worst_stab = min(stabilities)

        # ロバストネス = 安定性の加重平均（最近のテストを重視）
        n = len(stabilities)
        weights = [(i + 1) / n for i in range(n)]
        w_sum = sum(weights)
        weighted_robustness = sum(s * w for s, w in zip(stabilities, weights)) / w_sum

        n_vuln = sum(1 for s in stabilities if s < self._vuln_threshold)
        n_stable = len(stabilities) - n_vuln

        report = RobustnessReport(
            overall_robustness=round(weighted_robustness, 4),
            tests_conducted=len(self._test_results),
            vulnerable_states=n_vuln,
            stable_states=n_stable,
            avg_stability=round(avg_stab, 4),
            worst_stability=round(worst_stab, 4),
            mean_deviation=round(sum(deviations) / len(deviations), 4),
            timestamp=time.time(),
        )

        # 履歴に記録
        self._robustness_history.append(report.to_dict())
        if len(self._robustness_history) > ROBUSTNESS_HISTORY_SIZE:
            self._robustness_history = self._robustness_history[-ROBUSTNESS_HISTORY_SIZE:]

        return report

    # ── 脆弱状態 ──

    def get_vulnerable_states(self, limit: int = 20) -> List[Dict[str, Any]]:
        """脆弱と判定された状態一覧"""
        sorted_vulns = sorted(
            self._vulnerable_states.values(),
            key=lambda v: v.stability,
        )[:limit]
        return [
            {
                "state_id": v.state_id,
                "stability": v.stability,
                "worst_deviation": v.worst_deviation,
                "last_tested": v.last_tested,
                "test_count": v.test_count,
            }
            for v in sorted_vulns
        ]

    # ── 統計 ──

    def get_stats(self) -> Dict[str, Any]:
        """ロバストネス統計"""
        if not self._test_results:
            return {
                "total_tests": 0,
                "vulnerable_count": 0,
                "overall_robustness": 1.0,
            }
        stabilities = [r.stability for r in self._test_results]
        return {
            "total_tests": len(self._test_results),
            "vulnerable_count": len(self._vulnerable_states),
            "overall_robustness": round(sum(stabilities) / len(stabilities), 4),
            "worst_stability": round(min(stabilities), 4),
            "best_stability": round(max(stabilities), 4),
            "avg_deviation": round(
                sum(r.mean_deviation for r in self._test_results) / len(self._test_results), 4),
            "epsilon": self._epsilon,
            "history_size": len(self._robustness_history),
        }

    def get_recent_tests(self, limit: int = 20) -> List[Dict[str, Any]]:
        """直近のテスト結果"""
        return [r.to_dict() for r in self._test_results[-limit:]]

    def get_robustness_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """ロバストネスレポート履歴"""
        return self._robustness_history[-limit:]

    # ── 永続化 ──

    def _persist_state(self) -> None:
        if not self._persist:
            return
        try:
            data = {
                "test_results": [r.to_dict() for r in self._test_results[-MAX_TESTS:]],
                "vulnerable_states": {
                    k: {
                        "state_id": v.state_id,
                        "stability": v.stability,
                        "worst_deviation": v.worst_deviation,
                        "last_tested": v.last_tested,
                        "test_count": v.test_count,
                    }
                    for k, v in self._vulnerable_states.items()
                },
                "robustness_history": self._robustness_history[-ROBUSTNESS_HISTORY_SIZE:],
            }
            self._persist.parent.mkdir(parents=True, exist_ok=True)
            self._persist.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _restore(self) -> None:
        if not self._persist or not self._persist.exists():
            return
        try:
            data = json.loads(self._persist.read_text(encoding="utf-8"))
            for rd in data.get("test_results", []):
                self._test_results.append(PerturbationResult(**rd))
            for k, vd in data.get("vulnerable_states", {}).items():
                self._vulnerable_states[k] = VulnerableState(**vd)
            self._robustness_history = data.get("robustness_history", [])
        except Exception:
            pass
