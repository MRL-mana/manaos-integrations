#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 学習系・記憶系統合管理システム
RAG MemoryとLearning Systemの統合管理
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from rag_memory_optimized import RAGMemoryOptimized
from learning_system import LearningSystem
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("LearningMemoryIntegration")

# キャッシュシステムの取得
cache_system = get_unified_cache()


class LearningMemoryIntegration:
    """学習系・記憶系統合管理システム"""
    
    def __init__(
        self,
        memory_db_path: Optional[Path] = None,
        learning_storage_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            memory_db_path: RAG Memoryデータベースパス
            learning_storage_path: Learning Systemストレージパス
        """
        # RAG Memory（最適化版）
        self.memory = RAGMemoryOptimized(db_path=memory_db_path)
        
        # Learning System
        self.learning = LearningSystem(storage_path=learning_storage_path)
        
        logger.info("✅ 学習系・記憶系統合管理システム初期化完了")
    
    def record_and_learn(
        self,
        action: str,
        context: Dict[str, Any],
        result: Dict[str, Any],
        save_to_memory: bool = True
    ):
        """
        実行結果を記録し、学習・記憶に保存
        
        Args:
            action: 実行したアクション
            context: コンテキスト情報
            result: 実行結果
            save_to_memory: 記憶に保存するか
        """
        # Learning Systemに記録
        self.learning.record_usage(action, context, result)
        
        # 記憶に保存（成功した場合のみ）
        if save_to_memory and result.get("status") == "success":
            importance = self._calculate_importance_from_result(result)
            
            memory_content = f"アクション: {action}\n"
            memory_content += f"コンテキスト: {json.dumps(context, ensure_ascii=False)}\n"
            memory_content += f"結果: {json.dumps(result, ensure_ascii=False)}"
            
            self.memory.add_memory(
                content=memory_content,
                metadata={
                    "type": "action_result",
                    "action": action,
                    "context": context,
                    "result": result
                },
                force_importance=importance
            )
    
    def _calculate_importance_from_result(self, result: Dict[str, Any]) -> float:
        """実行結果から重要度を計算"""
        importance = 0.5  # ベーススコア
        
        # 成功した場合は重要度を上げる
        if result.get("status") == "success":
            importance += 0.2
        
        # エラーが発生した場合は重要度を上げる
        if result.get("error"):
            importance += 0.15
        
        return min(1.0, max(0.0, importance))
    
    def get_learned_preferences(self) -> Dict[str, Any]:
        """学習された好みを取得"""
        return self.learning.learn_preferences()
    
    def analyze_and_optimize(self) -> Dict[str, Any]:
        """分析して最適化提案を取得"""
        # パターン分析
        patterns = self.learning.analyze_patterns()
        
        # 記憶から重要な情報を取得
        important_memories = self.memory.search_memories("", limit=10, min_importance=0.7)
        
        # 最適化提案を生成
        recommendations = []
        
        # 成功率が低いアクションの改善提案
        for rec in patterns.get("recommendations", []):
            if rec["type"] == "low_success_rate":
                recommendations.append({
                    "type": "improve_action",
                    "action": rec["action"],
                    "suggestion": rec["suggestion"],
                    "priority": "high"
                })
        
        # 頻繁に使用されるアクションの自動化提案
        for rec in patterns.get("recommendations", []):
            if rec["type"] == "frequent_action":
                recommendations.append({
                    "type": "automate_action",
                    "action": rec["action"],
                    "suggestion": rec["suggestion"],
                    "priority": "medium"
                })
        
        return {
            "patterns": patterns,
            "important_memories": [m.entry_id for m in important_memories],
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_integrated_stats(self) -> Dict[str, Any]:
        """統合統計情報を取得"""
        # Learning Systemの統計
        learning_stats = {
            "total_actions": sum(len(records) for records in self.learning.usage_patterns.values()),
            "unique_actions": len(self.learning.usage_patterns),
            "preferences": self.learning.preferences
        }
        
        # Memory Systemの統計
        memory_stats = {
            "total_entries": len(self.memory.content_hash_map),
            "cache_stats": cache_system.get_stats()
        }
        
        return {
            "learning": learning_stats,
            "memory": memory_stats,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("学習系・記憶系統合管理システムテスト")
    print("=" * 60)
    
    integration = LearningMemoryIntegration()
    
    # 実行結果を記録
    integration.record_and_learn(
        action="test_action",
        context={"param": "value"},
        result={"status": "success", "data": "test"}
    )
    
    # 統計情報を取得
    stats = integration.get_integrated_stats()
    print(f"\n統計情報:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

