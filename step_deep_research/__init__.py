#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research: ManaOS版 専門調査員AI

専門調査員AIとして、証拠付きの結論と再現可能なログを提供します。
行動学習ベースの調査システムで、単なる情報検索を超えた価値を実現します。

主な機能:
- 役割分担アーキテクチャ（Planner / Research / Critic）
- 機械的品質評価（30項目ルーブリック）
- 予算ガード（コスト爆発防止）
- フェイルセーフ（事故らない設計）
- キャッシュシステム（再調査コスト削減）
- ソース品質フィルタ（一次情報優先）
- 専門テンプレート（技術選定/トラブル調査/最新動向）
- 自動逆算データ生成（自己成長ループ）

バージョン: 1.4.0
状態: Stable（安定版）
"""

__version__ = "1.4.0"
__author__ = "ManaOS Team"
__status__ = "stable"

# 主要クラスのエクスポート
from .schemas import (
    Plan,
    Citation,
    Summary,
    Contradiction,
    CritiqueResult,
    JobStatus,
    JobBudget,
    JobLog
)

__all__ = [
    "Plan",
    "Citation",
    "Summary",
    "Contradiction",
    "CritiqueResult",
    "JobStatus",
    "JobBudget",
    "JobLog"
]



