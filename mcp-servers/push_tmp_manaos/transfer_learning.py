#!/usr/bin/env python3
"""
Transfer Learning Engine
========================
異なるタスクタイプ・スキルドメイン間で知識を転移する。

主要概念:
  - Domain: タスクの種類 (e.g. "coding", "testing", "refactoring", "debugging")
  - DomainProfile: ドメインごとの学習済みパラメータ (重み, 成功率, 統計)
  - TransferPair: ドメイン間の類似度と転移係数
  - Knowledge Distillation: 高スコアドメインから低スコアドメインへ知識転送

使い方::

    tl = TransferLearning()
    tl.update_domain("coding",   score=0.9, difficulty="standard")
    tl.update_domain("testing",  score=0.6, difficulty="guided")

    transfer = tl.suggest_transfer("testing")
    # → {"source": "coding", "coefficient": 0.85, "expected_boost": 0.12}
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("rl_anything.transfer_learning")

# ═══════════════════════════════════════════════════════════
# データ構造
# ═══════════════════════════════════════════════════════════

@dataclass
class DomainProfile:
    """ドメインの学習済みプロファイル"""
    name: str
    total_tasks: int = 0
    total_score: float = 0.0
    success_count: int = 0
    # 重みベクトル (ドメインの知識を表現) — 次元は固定 8
    weights: List[float] = field(default_factory=lambda: [0.0] * 8)
    # 難易度分布
    difficulty_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_updated: str = ""

    @property
    def avg_score(self) -> float:
        return self.total_score / max(1, self.total_tasks)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.total_tasks)


@dataclass
class TransferResult:
    """転移結果"""
    source_domain: str
    target_domain: str
    similarity: float       # コサイン類似度
    coefficient: float      # 転移係数 (0-1)
    expected_boost: float   # 期待されるスコア改善量
    weights_transferred: List[float]
    confidence: float       # 転移の信頼度

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "similarity": round(self.similarity, 4),
            "coefficient": round(self.coefficient, 4),
            "expected_boost": round(self.expected_boost, 4),
            "confidence": round(self.confidence, 4),
        }


# ═══════════════════════════════════════════════════════════
# Transfer Learning Engine
# ═══════════════════════════════════════════════════════════

# 知識ベクトルの次元数
KNOWLEDGE_DIM = 8

# タスクタイプ → 初期重みバイアス (ドメイン特性を表現)
DOMAIN_PRIORS: Dict[str, List[float]] = {
    "coding":       [0.3, 0.1, 0.2, 0.0, 0.1, 0.2, 0.0, 0.1],
    "testing":      [0.1, 0.3, 0.1, 0.2, 0.0, 0.1, 0.1, 0.1],
    "debugging":    [0.2, 0.1, 0.3, 0.1, 0.1, 0.0, 0.1, 0.1],
    "refactoring":  [0.2, 0.0, 0.1, 0.3, 0.1, 0.1, 0.1, 0.1],
    "documentation":[0.0, 0.1, 0.0, 0.1, 0.3, 0.2, 0.1, 0.2],
    "devops":       [0.1, 0.1, 0.1, 0.0, 0.1, 0.3, 0.2, 0.1],
    "design":       [0.1, 0.0, 0.1, 0.2, 0.2, 0.0, 0.3, 0.1],
}

# 転移の減衰率 (類似度が低いほど転移効果が減衰)
TRANSFER_DECAY = 0.7
# 転移学習率 (knowledge distillation の際の混合率)
TRANSFER_LR = 0.2
# 最小データ量 (これ未満のドメインではソースとして使わない)
MIN_SOURCE_TASKS = 3


class TransferLearning:
    """
    ドメイン間の知識転移エンジン。
    各ドメインの重みベクトルを更新し、類似ドメインの知識を活用する。
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._domains: Dict[str, DomainProfile] = {}
        self._transfer_history: List[Dict[str, Any]] = []
        self._persist_path = persist_path

        # 設定
        cfg = config or {}
        self._transfer_lr = cfg.get("transfer_lr", TRANSFER_LR)
        self._min_source_tasks = cfg.get("min_source_tasks", MIN_SOURCE_TASKS)

        self._restore()

    # ───────────────── ドメイン更新 ─────────────────

    def update_domain(
        self,
        domain: str,
        score: float,
        outcome: str = "success",
        difficulty: str = "standard",
    ) -> Dict[str, Any]:
        """
        タスク完了時にドメインプロファイルを更新。
        重みベクトルを score に基づいて調整。
        """
        profile = self._get_or_create(domain)
        profile.total_tasks += 1
        profile.total_score += score
        if outcome == "success":
            profile.success_count += 1
        profile.difficulty_counts[difficulty] = profile.difficulty_counts.get(difficulty, 0) + 1
        profile.last_updated = datetime.now().isoformat()

        # 重みベクトル更新: score が高い → 現在の重みを強化、低い → 減衰
        lr = 0.1
        for i in range(KNOWLEDGE_DIM):
            # Score に応じてドメインプライオアの方向に重みを調整
            prior = DOMAIN_PRIORS.get(domain, [0.0] * KNOWLEDGE_DIM)
            pi = prior[i] if i < len(prior) else 0.0
            # 高スコア → プライオアに近づく (強化学習的更新)
            target = pi * score + profile.weights[i] * (1 - score)
            profile.weights[i] += lr * (target - profile.weights[i])

        self._persist()
        return {
            "domain": domain,
            "total_tasks": profile.total_tasks,
            "avg_score": round(profile.avg_score, 4),
            "success_rate": round(profile.success_rate, 4),
        }

    def _get_or_create(self, domain: str) -> DomainProfile:
        """ドメインプロファイルを取得、なければ作成"""
        if domain not in self._domains:
            prior = DOMAIN_PRIORS.get(domain, [0.0] * KNOWLEDGE_DIM)
            self._domains[domain] = DomainProfile(
                name=domain,
                weights=list(prior),
            )
        return self._domains[domain]

    # ───────────────── 類似度計算 ─────────────────

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """コサイン類似度"""
        dot = sum(ai * bi for ai, bi in zip(a, b))
        norm_a = math.sqrt(sum(ai ** 2 for ai in a))
        norm_b = math.sqrt(sum(bi ** 2 for bi in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get_domain_similarity(self, domain_a: str, domain_b: str) -> float:
        """2 ドメイン間の類似度"""
        a = self._get_or_create(domain_a)
        b = self._get_or_create(domain_b)
        return self._cosine_similarity(a.weights, b.weights)

    def get_similarity_matrix(self) -> Dict[str, Dict[str, float]]:
        """全ドメインペアの類似度行列"""
        names = list(self._domains.keys())
        matrix: Dict[str, Dict[str, float]] = {}
        for a in names:
            matrix[a] = {}
            for b in names:
                matrix[a][b] = round(self.get_domain_similarity(a, b), 4)
        return matrix

    # ───────────────── 転移提案 ─────────────────

    def suggest_transfer(self, target_domain: str) -> Optional[TransferResult]:
        """
        target_domain に最適な転移元を見つけて提案する。
        類似度 × ソースの品質で最良のペアを選定。
        """
        target = self._get_or_create(target_domain)
        best: Optional[TransferResult] = None
        best_score = -1.0

        for name, source in self._domains.items():
            if name == target_domain:
                continue
            if source.total_tasks < self._min_source_tasks:
                continue

            similarity = self._cosine_similarity(source.weights, target.weights)
            if similarity < 0.1:
                continue  # 類似度が低すぎるドメインはスキップ

            # 転移係数 = 類似度 × ソースの品質
            quality = source.avg_score * (0.5 + 0.5 * source.success_rate)
            coefficient = similarity * quality * TRANSFER_DECAY

            # 期待ブースト = 転移係数 × (ソーススコア - ターゲットスコア) の正の部分
            score_gap = max(0, source.avg_score - target.avg_score)
            expected_boost = coefficient * score_gap * self._transfer_lr

            # 信頼度: ソースのデータ量に比例
            confidence = min(1.0, source.total_tasks / 20.0) * min(1.0, similarity + 0.3)

            # 総合スコア = 転移係数 × 信頼度
            composite = coefficient * confidence
            if composite > best_score:
                best_score = composite
                # 転移する重み = ソース重みとターゲット重みの混合
                transferred = [
                    target.weights[i] + self._transfer_lr * coefficient * (source.weights[i] - target.weights[i])
                    for i in range(KNOWLEDGE_DIM)
                ]
                best = TransferResult(
                    source_domain=name,
                    target_domain=target_domain,
                    similarity=similarity,
                    coefficient=coefficient,
                    expected_boost=expected_boost,
                    weights_transferred=transferred,
                    confidence=confidence,
                )

        return best

    def apply_transfer(self, target_domain: str) -> Optional[Dict[str, Any]]:
        """
        suggest_transfer の結果を適用し、ターゲットの重みを更新。
        """
        transfer = self.suggest_transfer(target_domain)
        if transfer is None:
            return None

        target = self._get_or_create(target_domain)
        old_weights = list(target.weights)
        target.weights = transfer.weights_transferred
        target.last_updated = datetime.now().isoformat()

        record = {
            **transfer.to_dict(),
            "ts": datetime.now().isoformat(),
            "old_weights": old_weights,
            "new_weights": list(target.weights),
        }
        self._transfer_history.append(record)

        # 履歴上限 (最新 100 件)
        if len(self._transfer_history) > 100:
            self._transfer_history = self._transfer_history[-100:]

        self._persist()
        return record

    # ───────────────── ドメイン推定 ─────────────────

    def infer_domain(self, task_description: str) -> str:
        """
        タスク説明からドメインを推定する (簡易ヒューリスティック)。
        """
        desc = task_description.lower()
        domain_keywords = {
            "coding":       ["implement", "add", "create", "build", "write", "code", "function", "class", "component"],
            "testing":      ["test", "spec", "assert", "coverage", "verify", "check", "validate"],
            "debugging":    ["debug", "fix", "bug", "error", "issue", "crash", "broken", "wrong"],
            "refactoring":  ["refactor", "clean", "restructure", "simplify", "extract", "move", "rename"],
            "documentation":["document", "readme", "doc", "comment", "explain", "describe"],
            "devops":       ["deploy", "docker", "ci", "cd", "pipeline", "config", "infra", "server", "kubernetes"],
            "design":       ["design", "architecture", "plan", "structure", "pattern", "interface"],
        }

        scores: Dict[str, int] = defaultdict(int)
        for domain, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in desc:
                    scores[domain] += 1

        if not scores:
            return "coding"  # デフォルト
        return max(scores, key=scores.get)  # type: ignore[call-arg]

    # ───────────────── 統計 ─────────────────

    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        domains = {}
        for name, profile in self._domains.items():
            domains[name] = {
                "total_tasks": profile.total_tasks,
                "avg_score": round(profile.avg_score, 4),
                "success_rate": round(profile.success_rate, 4),
                "last_updated": profile.last_updated,
            }

        return {
            "domain_count": len(self._domains),
            "domains": domains,
            "transfer_count": len(self._transfer_history),
            "recent_transfers": self._transfer_history[-5:] if self._transfer_history else [],
        }

    def get_domain_details(self, domain: str) -> Dict[str, Any]:
        """特定ドメインの詳細"""
        profile = self._get_or_create(domain)
        return {
            "name": profile.name,
            "total_tasks": profile.total_tasks,
            "avg_score": round(profile.avg_score, 4),
            "success_rate": round(profile.success_rate, 4),
            "weights": [round(w, 4) for w in profile.weights],
            "difficulty_distribution": dict(profile.difficulty_counts),
            "last_updated": profile.last_updated,
        }

    # ───────────────── 永続化 ─────────────────

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "domains": {
                    name: {
                        "total_tasks": p.total_tasks,
                        "total_score": p.total_score,
                        "success_count": p.success_count,
                        "weights": p.weights,
                        "difficulty_counts": dict(p.difficulty_counts),
                        "last_updated": p.last_updated,
                    }
                    for name, p in self._domains.items()
                },
                "transfer_history": self._transfer_history[-100:],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("transfer persist failed: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            for name, ddata in data.get("domains", {}).items():
                profile = DomainProfile(
                    name=name,
                    total_tasks=ddata.get("total_tasks", 0),
                    total_score=ddata.get("total_score", 0),
                    success_count=ddata.get("success_count", 0),
                    weights=ddata.get("weights", [0.0] * KNOWLEDGE_DIM),
                    difficulty_counts=defaultdict(int, ddata.get("difficulty_counts", {})),
                    last_updated=ddata.get("last_updated", ""),
                )
                self._domains[name] = profile
            self._transfer_history = data.get("transfer_history", [])
        except Exception as e:
            _log.warning("transfer restore failed: %s", e)
