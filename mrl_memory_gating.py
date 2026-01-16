#!/usr/bin/env python3
"""
MRL Memory Gating
メモリ汚染に対する防御機構
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MemoryGating:
    """
    ゲーティング機構
    
    メモリ汚染に対する防御:
    - 矛盾検出
    - 低確度扱い
    - 強く断言しない
    """
    
    def __init__(self):
        """初期化"""
        # 信頼度閾値
        self.confidence_threshold = 0.7
        
        # 矛盾検出の閾値
        self.conflict_threshold = 0.5
        
        logger.info("✅ Memory Gating初期化完了")
    
    def gate_entry(
        self,
        entry: Dict[str, Any],
        existing_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        エントリにゲートを適用
        
        Args:
            entry: 新しいエントリ
            existing_entries: 既存エントリのリスト
        
        Returns:
            ゲート適用後のエントリ
        """
        confidence = self._get_confidence(entry)
        
        # 矛盾チェック
        has_conflict = self._check_conflict(entry, existing_entries)
        
        # ゲート重みを計算
        if has_conflict:
            # 矛盾がある場合は低ゲート
            gate_weight = 0.3
            entry["gated"] = True
            entry["gate_reason"] = "conflict_detected"
        elif confidence < self.confidence_threshold:
            # 低確度の場合は中ゲート
            gate_weight = 0.5
            entry["gated"] = True
            entry["gate_reason"] = "low_confidence"
        else:
            # 高確度の場合は高ゲート
            gate_weight = 0.8
            entry["gated"] = False
            entry["gate_reason"] = "high_confidence"
        
        entry["gate_weight"] = gate_weight
        entry["original_confidence"] = confidence
        entry["has_conflict"] = has_conflict
        
        return entry
    
    def _get_confidence(self, entry: Dict[str, Any]) -> float:
        """信頼度を取得"""
        confidence_map = {
            "low": 0.3,
            "med": 0.6,
            "high": 0.9
        }
        
        confidence_str = entry.get("confidence", "low")
        return confidence_map.get(confidence_str, 0.3)
    
    def _check_conflict(
        self,
        entry: Dict[str, Any],
        existing_entries: List[Dict[str, Any]]
    ) -> bool:
        """矛盾をチェック"""
        entry_key = entry.get("key", "").lower()
        entry_value = entry.get("value", "").lower()
        
        for existing in existing_entries:
            existing_key = existing.get("key", "").lower()
            existing_value = existing.get("value", "").lower()
            
            # キーが同じで値が異なる場合
            if entry_key == existing_key:
                if entry_value != existing_value:
                    # 矛盾検出（長さチェックを緩和：3文字以上で矛盾とみなす）
                    if len(entry_value) >= 3 and len(existing_value) >= 3:
                        # 完全に異なる値の場合（部分一致でない）
                        if entry_value not in existing_value and existing_value not in entry_value:
                            return True
        
        return False
    
    def filter_by_gate(
        self,
        entries: List[Dict[str, Any]],
        min_gate_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        ゲート重みでフィルタ
        
        Args:
            entries: エントリのリスト
            min_gate_weight: 最小ゲート重み
        
        Returns:
            フィルタ済みエントリ
        """
        filtered = [
            entry for entry in entries
            if entry.get("gate_weight", 0) >= min_gate_weight
        ]
        
        return filtered
    
    def add_uncertainty_marker(
        self,
        entry: Dict[str, Any]
    ) -> str:
        """
        不確実性マーカーを追加
        
        Args:
            entry: エントリ
        
        Returns:
            マーカー付きテキスト
        """
        gate_weight = entry.get("gate_weight", 1.0)
        has_conflict = entry.get("has_conflict", False)
        
        value = entry.get("value", "")
        
        if has_conflict:
            return f"[矛盾の可能性あり] {value}"
        elif gate_weight < 0.5:
            return f"[低確度] {value}"
        elif gate_weight < 0.7:
            return f"[中確度] {value}"
        else:
            return value
