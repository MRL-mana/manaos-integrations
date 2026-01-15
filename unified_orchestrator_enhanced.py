#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Unified Orchestrator Enhanced
記憶系・学習系・人格系・自律系・秘書系を統合した強化版
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 基本オーケストレーター
from unified_orchestrator import UnifiedOrchestrator

# 記憶系・学習系
from rag_memory_enhanced_v2 import RAGMemoryEnhancedV2
from learning_system_enhanced import LearningSystemEnhanced

# 人格系・自律系・秘書系
from personality_system_enhanced import PersonalitySystemEnhanced
from autonomy_system_enhanced import AutonomySystemEnhanced
from secretary_system_optimized import SecretarySystemOptimized

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedOrchestratorEnhanced")


class UnifiedOrchestratorEnhanced(UnifiedOrchestrator):
    """Unified Orchestrator Enhanced（記憶系・学習系・人格系・自律系・秘書系統合版）"""
    
    def __init__(
        self,
        intent_router_url: str = "http://localhost:5100",
        task_planner_url: str = "http://localhost:5101",
        task_critic_url: str = "http://localhost:5102",
        task_queue_url: str = "http://localhost:5104",
        executor_url: Optional[str] = None,
        rag_memory_url: str = "http://localhost:5103",
        learning_system_url: Optional[str] = None,
        personality_url: str = "http://localhost:5123",
        autonomy_url: str = "http://localhost:5124",
        secretary_url: str = "http://localhost:5125",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            intent_router_url: Intent Router API URL
            task_planner_url: Task Planner API URL
            task_critic_url: Task Critic API URL
            task_queue_url: Task Queue API URL
            executor_url: Executor API URL
            rag_memory_url: RAG Memory API URL
            learning_system_url: Learning System API URL
            personality_url: Personality System API URL
            autonomy_url: Autonomy System API URL
            secretary_url: Secretary System API URL
            config_path: 設定ファイルのパス
        """
        # 基本オーケストレーターを初期化
        super().__init__(
            intent_router_url=intent_router_url,
            task_planner_url=task_planner_url,
            task_critic_url=task_critic_url,
            task_queue_url=task_queue_url,
            executor_url=executor_url,
            rag_memory_url=rag_memory_url,
            learning_system_url=learning_system_url,
            config_path=config_path
        )
        
        # 記憶系・学習系（直接インポート）
        try:
            self.rag_memory_enhanced = RAGMemoryEnhancedV2()
            logger.info("✅ RAG Memory Enhanced v2統合完了")
        except Exception as e:
            logger.warning(f"⚠️ RAG Memory Enhanced統合エラー: {e}")
            self.rag_memory_enhanced = None
        
        try:
            self.learning_system_enhanced = LearningSystemEnhanced()
            logger.info("✅ Learning System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Learning System Enhanced統合エラー: {e}")
            self.learning_system_enhanced = None
        
        # 人格系・自律系・秘書系（直接インポート）
        try:
            self.personality_enhanced = PersonalitySystemEnhanced()
            logger.info("✅ Personality System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Personality System Enhanced統合エラー: {e}")
            self.personality_enhanced = None
        
        try:
            self.autonomy_enhanced = AutonomySystemEnhanced(
                orchestrator_url=f"http://localhost:5106",
                learning_system_url=learning_system_url
            )
            logger.info("✅ Autonomy System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Autonomy System Enhanced統合エラー: {e}")
            self.autonomy_enhanced = None
        
        try:
            self.secretary_optimized = SecretarySystemOptimized(
                orchestrator_url=f"http://localhost:5106"
            )
            logger.info("✅ Secretary System Optimized統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Secretary System Optimized統合エラー: {e}")
            self.secretary_optimized = None
        
        logger.info("✅ Unified Orchestrator Enhanced初期化完了")
    
    async def execute(
        self,
        text: str,
        mode: str = "auto",
        auto_evaluate: bool = True,
        save_to_memory: bool = True,
        use_personality: bool = True,
        use_autonomy: bool = True,
        use_secretary: bool = True
    ):
        """
        実行（記憶系・学習系・人格系・自律系・秘書系を統合）
        
        Args:
            text: 入力テキスト
            mode: 実行モード
            auto_evaluate: 自動評価
            save_to_memory: 記憶に保存
            use_personality: 人格を使用
            use_autonomy: 自律を使用
            use_secretary: 秘書を使用
        
        Returns:
            実行結果
        """
        # 人格を考慮した応答スタイルを取得
        personality_context = None
        if use_personality and self.personality_enhanced:
            try:
                personality_response = self.personality_enhanced.get_personality_response(text)
                personality_context = personality_response.get("personality", {})
            except Exception as e:
                logger.warning(f"人格応答取得エラー: {e}")
        
        # 記憶から関連情報を検索
        related_memories = []
        if self.rag_memory_enhanced:
            try:
                related_memories = self.rag_memory_enhanced.search_memories(text, limit=5)
            except Exception as e:
                logger.warning(f"記憶検索エラー: {e}")
        
        # 学習システムから予測を取得
        predictions = []
        if self.learning_system_enhanced:
            try:
                predictions = self.learning_system_enhanced.predict_next_action({
                    "text": text,
                    "mode": mode
                })
            except Exception as e:
                logger.warning(f"予測取得エラー: {e}")
        
        # 基本オーケストレーターで実行
        result = await super().execute(
            text=text,
            mode=mode,
            auto_evaluate=auto_evaluate,
            save_to_memory=save_to_memory
        )
        
        # 自律システムで予測的タスクを実行
        if use_autonomy and self.autonomy_enhanced:
            try:
                autonomous_results = await self.autonomy_enhanced.predict_and_execute_tasks()
                if autonomous_results:
                    logger.info(f"自律タスク実行: {len(autonomous_results)}件")
            except Exception as e:
                logger.warning(f"自律タスク実行エラー: {e}")
        
        # 秘書システムに報告を追加
        if use_secretary and self.secretary_optimized and result.status == "completed":
            try:
                from secretary_system_optimized import Report
                report = Report(
                    report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    report_type="execution",
                    title=f"実行完了: {text[:50]}",
                    content=json.dumps(result.result or {}, ensure_ascii=False),
                    generated_at=datetime.now().isoformat(),
                    metadata={
                        "personality": personality_context.get("name") if personality_context else None,
                        "related_memories_count": len(related_memories),
                        "predictions_count": len(predictions)
                    }
                )
                self.secretary_optimized.add_report(report)
            except Exception as e:
                logger.warning(f"報告追加エラー: {e}")
        
        # 結果に追加情報を付与
        result.enhanced_info = {
            "personality": personality_context,
            "related_memories_count": len(related_memories),
            "predictions_count": len(predictions)
        }
        
        return result
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """強化版状態を取得"""
        base_status = {
            "orchestrator": "operational",
            "enhanced_systems": {}
        }
        
        # 記憶系・学習系の状態
        if self.rag_memory_enhanced:
            try:
                stats = self.rag_memory_enhanced.get_statistics()
                base_status["enhanced_systems"]["rag_memory"] = {
                    "available": True,
                    "total_entries": stats.get("total_entries", 0)
                }
            except:
                base_status["enhanced_systems"]["rag_memory"] = {"available": False}
        
        if self.learning_system_enhanced:
            try:
                base_status["enhanced_systems"]["learning_system"] = {
                    "available": True,
                    "total_actions": len(self.learning_system_enhanced.usage_patterns) if hasattr(self.learning_system_enhanced, "usage_patterns") else 0
                }
            except:
                base_status["enhanced_systems"]["learning_system"] = {"available": False}
        
        # 人格系・自律系・秘書系の状態
        if self.personality_enhanced:
            try:
                stats = self.personality_enhanced.get_personality_stats()
                base_status["enhanced_systems"]["personality"] = {
                    "available": True,
                    "current_persona": stats.get("current_persona", {}).get("name")
                }
            except:
                base_status["enhanced_systems"]["personality"] = {"available": False}
        
        if self.autonomy_enhanced:
            try:
                stats = self.autonomy_enhanced.get_autonomy_stats()
                base_status["enhanced_systems"]["autonomy"] = {
                    "available": True,
                    "autonomy_level": stats.get("autonomy_level")
                }
            except:
                base_status["enhanced_systems"]["autonomy"] = {"available": False}
        
        if self.secretary_optimized:
            try:
                pending = self.secretary_optimized.get_pending_reminders()
                base_status["enhanced_systems"]["secretary"] = {
                    "available": True,
                    "pending_reminders": len(pending)
                }
            except:
                base_status["enhanced_systems"]["secretary"] = {"available": False}
        
        return base_status


def main():
    """テスト用メイン関数"""
    print("Unified Orchestrator Enhancedテスト")
    print("=" * 60)
    
    orchestrator = UnifiedOrchestratorEnhanced()
    
    # 状態を取得
    status = orchestrator.get_enhanced_status()
    print(f"\n強化版状態:")
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()






















