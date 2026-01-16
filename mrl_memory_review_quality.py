#!/usr/bin/env python3
"""
MRL Memory Review Quality
復習効果の成功条件を数値化（品質指標）
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


class ReviewQualityMetrics:
    """
    復習効果の成功条件を数値化
    
    指標:
    - 正答率（accuracy）
    - 参照率（reference_rate）
    - 矛盾率（conflict_rate）
    """
    
    def __init__(self):
        """初期化"""
        self.review_history: List[Dict[str, Any]] = []
        logger.info("✅ Review Quality Metrics初期化完了")
    
    def measure_review_effect(
        self,
        first_pass: Dict[str, Any],
        second_pass: Dict[str, Any],
        query: str,
        correct_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        復習効果を測定
        
        Args:
            first_pass: 1回目の結果
            second_pass: 2回目の結果
            query: クエリ
            correct_answer: 正解（オプション）
        
        Returns:
            測定結果
        """
        # 1. 正答率（正解がある場合）
        accuracy_first = None
        accuracy_second = None
        if correct_answer:
            accuracy_first = self._calculate_accuracy(first_pass, correct_answer)
            accuracy_second = self._calculate_accuracy(second_pass, correct_answer)
        
        # 2. 参照率（メモリから参照できたか）
        reference_rate_first = self._calculate_reference_rate(first_pass)
        reference_rate_second = self._calculate_reference_rate(second_pass)
        
        # 3. 矛盾率
        conflict_rate_first = self._calculate_conflict_rate(first_pass)
        conflict_rate_second = self._calculate_conflict_rate(second_pass)
        
        # 改善度を計算
        improvement = {
            "accuracy_improvement": (
                accuracy_second - accuracy_first
                if accuracy_first is not None and accuracy_second is not None
                else None
            ),
            "reference_rate_improvement": reference_rate_second - reference_rate_first,
            "conflict_rate_change": conflict_rate_second - conflict_rate_first
        }
        
        result = {
            "first_pass": {
                "accuracy": accuracy_first,
                "reference_rate": reference_rate_first,
                "conflict_rate": conflict_rate_first
            },
            "second_pass": {
                "accuracy": accuracy_second,
                "reference_rate": reference_rate_second,
                "conflict_rate": conflict_rate_second
            },
            "improvement": improvement,
            "timestamp": datetime.now().isoformat()
        }
        
        self.review_history.append(result)
        
        return result
    
    def _calculate_accuracy(
        self,
        result: Dict[str, Any],
        correct_answer: str
    ) -> float:
        """
        正答率を計算
        
        Args:
            result: 結果
            correct_answer: 正解
        
        Returns:
            正答率（0.0-1.0）
        """
        # 簡易実装：結果に正解が含まれているか
        response = result.get("response", "").lower()
        correct = correct_answer.lower()
        
        if correct in response:
            return 1.0
        else:
            # 部分一致でスコアを計算
            # より高度な実装では、意味的類似度を使用
            return 0.0
    
    def _calculate_reference_rate(self, result: Dict[str, Any]) -> float:
        """
        参照率を計算
        
        Args:
            result: 結果
        
        Returns:
            参照率（0.0-1.0）
        """
        # メモリが使用されたか
        memory_used = result.get("memory_used", False)
        memory_context_length = result.get("memory_context_length", 0)
        
        if memory_used and memory_context_length > 0:
            return 1.0
        else:
            return 0.0
    
    def _calculate_conflict_rate(self, result: Dict[str, Any]) -> float:
        """
        矛盾率を計算
        
        Args:
            result: 結果
        
        Returns:
            矛盾率（0.0-1.0）
        """
        conflicts = result.get("conflicts", [])
        total_results = result.get("resolved_count", 1)
        
        if total_results == 0:
            return 0.0
        
        return len(conflicts) / total_results
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """
        復習統計を取得
        
        Returns:
            統計情報
        """
        if not self.review_history:
            return {}
        
        improvements = [
            r["improvement"] for r in self.review_history
            if r["improvement"].get("reference_rate_improvement") is not None
        ]
        
        if not improvements:
            return {}
        
        reference_improvements = [
            i["reference_rate_improvement"] for i in improvements
        ]
        conflict_changes = [
            i["conflict_rate_change"] for i in improvements
        ]
        
        return {
            "total_reviews": len(self.review_history),
            "mean_reference_improvement": sum(reference_improvements) / len(reference_improvements),
            "mean_conflict_change": sum(conflict_changes) / len(conflict_changes),
            "positive_improvements": sum(1 for i in reference_improvements if i > 0)
        }
