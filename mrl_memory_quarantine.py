#!/usr/bin/env python3
"""
MRL Memory Quarantine
矛盾/低確度の隔離システム
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MemoryQuarantine:
    """
    矛盾/低確度の隔離システム
    
    構造:
    - active_memory（回答に使う）
    - quarantine_memory（矛盾/低確度の隔離）
    - evidence_log（理由）
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            memory_dir: メモリディレクトリ
        """
        if memory_dir is None:
            memory_dir = Path(__file__).parent / "mrl_memory"
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.quarantine_path = self.memory_dir / "quarantine.jsonl"
        self.evidence_log_path = self.memory_dir / "evidence_log.jsonl"
        
        logger.info("✅ Memory Quarantine初期化完了")
    
    def resolve_conflict_with_quarantine(
        self,
        entry1: Dict[str, Any],
        entry2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        矛盾を解決して勝者決定＋敗者隔離
        
        Args:
            entry1: エントリ1
            entry2: エントリ2
        
        Returns:
            解決結果（active, quarantined, evidence）
        """
        # 優先スコアを計算
        score1 = self._calculate_priority_score(entry1)
        score2 = self._calculate_priority_score(entry2)
        
        # 勝者を決定
        if score1 >= score2:
            winner = entry1
            loser = entry2
            winner_score = score1
            loser_score = score2
        else:
            winner = entry2
            loser = entry1
            winner_score = score2
            loser_score = score1
        
        # 敗者を隔離
        self._quarantine_entry(loser, reason="conflict_lost", winner=winner)
        
        # 証拠ログに記録
        self._log_evidence(
            winner=winner,
            loser=loser,
            winner_score=winner_score,
            loser_score=loser_score,
            reason="conflict_resolution"
        )
        
        return {
            "active": winner,
            "quarantined": loser,
            "evidence": {
                "winner_score": winner_score,
                "loser_score": loser_score,
                "reason": "conflict_resolution"
            }
        }
    
    def _calculate_priority_score(self, entry: Dict[str, Any]) -> float:
        """
        優先スコアを計算
        
        スコア = recency（新しさ） + confidence（確度） + source_weight（根拠の強さ）
        
        Args:
            entry: エントリ
        
        Returns:
            優先スコア（0.0-3.0）
        """
        # recency（新しさ）
        recency = self._calculate_recency(entry)
        
        # confidence（確度）
        confidence_map = {"low": 0.3, "med": 0.6, "high": 0.9}
        confidence = confidence_map.get(entry.get("confidence", "low"), 0.3)
        
        # source_weight（根拠の強さ）
        source = entry.get("source", "unknown")
        source_weights = {
            "user_input": 1.0,  # ユーザー直入力
            "external_document": 0.8,  # 外部文書
            "rag": 0.6,  # RAG（長期記憶）
            "fwpkm": 0.7,  # FWPKM（短期記憶）
            "unknown": 0.5
        }
        source_weight = source_weights.get(source, 0.5)
        
        # 総合スコア
        total_score = recency + confidence + source_weight
        
        return total_score
    
    def _calculate_recency(self, entry: Dict[str, Any]) -> float:
        """
        新しさスコアを計算
        
        Args:
            entry: エントリ
        
        Returns:
            新しさスコア（0.0-1.0）
        """
        timestamp = entry.get("timestamp", "")
        if not timestamp:
            return 0.5  # タイムスタンプがない場合は中間値
        
        try:
            entry_time = datetime.fromisoformat(timestamp)
            now = datetime.now()
            age_hours = (now - entry_time).total_seconds() / 3600
            
            # 24時間以内なら1.0、それ以降は減衰
            if age_hours <= 24:
                return 1.0
            elif age_hours <= 168:  # 1週間
                return 0.7
            elif age_hours <= 720:  # 1ヶ月
                return 0.4
            else:
                return 0.1
        except Exception:
            return 0.5
    
    def _quarantine_entry(
        self,
        entry: Dict[str, Any],
        reason: str,
        winner: Optional[Dict[str, Any]] = None
    ):
        """
        エントリを隔離
        
        Args:
            entry: 隔離するエントリ
            reason: 隔離理由
            winner: 勝者（矛盾の場合）
        """
        quarantined_entry = {
            **entry,
            "quarantined_at": datetime.now().isoformat(),
            "quarantine_reason": reason,
            "winner": winner.get("key", "") if winner else None
        }
        
        with open(self.quarantine_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(quarantined_entry, ensure_ascii=False) + '\n')
        
        logger.info(f"エントリを隔離: {entry.get('key', 'unknown')} (理由: {reason})")
    
    def _log_evidence(
        self,
        winner: Dict[str, Any],
        loser: Dict[str, Any],
        winner_score: float,
        loser_score: float,
        reason: str
    ):
        """
        証拠ログに記録
        
        Args:
            winner: 勝者
            loser: 敗者
            winner_score: 勝者のスコア
            loser_score: 敗者のスコア
            reason: 理由
        """
        evidence = {
            "timestamp": datetime.now().isoformat(),
            "winner": {
                "key": winner.get("key", ""),
                "value": winner.get("value", "")[:100],
                "source": winner.get("source", ""),
                "confidence": winner.get("confidence", ""),
                "score": winner_score
            },
            "loser": {
                "key": loser.get("key", ""),
                "value": loser.get("value", "")[:100],
                "source": loser.get("source", ""),
                "confidence": loser.get("confidence", ""),
                "score": loser_score
            },
            "reason": reason
        }
        
        with open(self.evidence_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(evidence, ensure_ascii=False) + '\n')
