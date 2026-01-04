#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 ManaOS完全統合システム
マナOSコア + 記憶系 + 学習系 + 人格系 + 自律系 + 秘書系の完全統合
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

# マナOSコアシステム
from unified_orchestrator import UnifiedOrchestrator

# 記憶系・学習系
from rag_memory_enhanced_v2 import RAGMemoryEnhancedV2
from learning_system_enhanced import LearningSystemEnhanced
from learning_memory_integration import LearningMemoryIntegration

# 人格系・自律系・秘書系
from personality_system_enhanced import PersonalitySystemEnhanced
from autonomy_system_enhanced import AutonomySystemEnhanced
from secretary_system_optimized import SecretarySystemOptimized
from personality_autonomy_secretary_integration import PersonalityAutonomySecretaryIntegration

# 最適化モジュール
from manaos_async_client import AsyncUnifiedAPIClient
from unified_cache_system import get_unified_cache
from metrics_collector_optimized import MetricsCollectorOptimized, MetricType

# ローカルLLMシステム
try:
    from llm_optimization import LLMOptimization
    LLM_OPTIMIZATION_AVAILABLE = True
except ImportError:
    LLM_OPTIMIZATION_AVAILABLE = False
    logger.warning("⚠️ LLM Optimizationが利用できません")

try:
    from local_llm_integration import local_llm_systems
    from local_llm_unified import LocalLLMUnified
    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False

# GitHub統合
try:
    from github_integration import GitHubIntegration
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# n8n統合
try:
    from n8n_integration import N8NIntegration
    N8N_AVAILABLE = True
except ImportError:
    N8N_AVAILABLE = False

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ManaOSCompleteIntegration")

# キャッシュシステムの取得
cache_system = get_unified_cache()


class ManaOSCompleteIntegration:
    """マナOS完全統合システム"""
    
    def __init__(
        self,
        orchestrator_url: str = "http://localhost:5106",
        rag_memory_url: str = "http://localhost:5103",
        learning_system_url: str = "http://localhost:5126",
        personality_url: str = "http://localhost:5123",
        autonomy_url: str = "http://localhost:5124",
        secretary_url: str = "http://localhost:5125"
    ):
        """
        初期化
        
        Args:
            orchestrator_url: Unified Orchestrator API URL
            rag_memory_url: RAG Memory API URL
            learning_system_url: Learning System API URL
            personality_url: Personality System API URL
            autonomy_url: Autonomy System API URL
            secretary_url: Secretary System API URL
        """
        # マナOSコアシステム
        self.orchestrator = UnifiedOrchestrator(
            rag_memory_url=rag_memory_url,
            learning_system_url=learning_system_url
        )
        
        # 記憶系・学習系（直接インポート）
        try:
            self.rag_memory = RAGMemoryEnhancedV2()
            logger.info("✅ RAG Memory Enhanced v2統合完了")
        except Exception as e:
            logger.warning(f"⚠️ RAG Memory統合エラー: {e}")
            self.rag_memory = None
        
        try:
            self.learning_system = LearningSystemEnhanced()
            logger.info("✅ Learning System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Learning System統合エラー: {e}")
            self.learning_system = None
        
        try:
            self.learning_memory = LearningMemoryIntegration()
            logger.info("✅ Learning Memory Integration統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Learning Memory統合エラー: {e}")
            self.learning_memory = None
        
        # 人格系・自律系・秘書系（直接インポート）
        try:
            self.personality = PersonalitySystemEnhanced()
            logger.info("✅ Personality System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Personality System統合エラー: {e}")
            self.personality = None
        
        try:
            self.autonomy = AutonomySystemEnhanced(
                orchestrator_url=orchestrator_url,
                learning_system_url=learning_system_url
            )
            logger.info("✅ Autonomy System Enhanced統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Autonomy System統合エラー: {e}")
            self.autonomy = None
        
        try:
            self.secretary = SecretarySystemOptimized(orchestrator_url=orchestrator_url)
            logger.info("✅ Secretary System Optimized統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Secretary System統合エラー: {e}")
            self.secretary = None
        
        try:
            self.pas_integration = PersonalityAutonomySecretaryIntegration(
                orchestrator_url=orchestrator_url,
                learning_system_url=learning_system_url
            )
            logger.info("✅ Personality-Autonomy-Secretary Integration統合完了")
        except Exception as e:
            logger.warning(f"⚠️ PAS Integration統合エラー: {e}")
            self.pas_integration = None
        
        # メトリクス収集
        try:
            self.metrics = MetricsCollectorOptimized()
            logger.info("✅ Metrics Collector統合完了")
        except Exception as e:
            logger.warning(f"⚠️ Metrics Collector統合エラー: {e}")
            self.metrics = None
        
        # ローカルLLMシステム
        try:
            if LLM_OPTIMIZATION_AVAILABLE:
                self.llm_optimization = LLMOptimization()
                logger.info("✅ LLM Optimization統合完了")
            else:
                self.llm_optimization = None
        except Exception as e:
            logger.warning(f"⚠️ LLM Optimization統合エラー: {e}")
            self.llm_optimization = None
        
        try:
            if LOCAL_LLM_AVAILABLE:
                self.local_llm_unified = LocalLLMUnified()
                logger.info("✅ Local LLM Unified統合完了")
            else:
                self.local_llm_unified = None
        except Exception as e:
            logger.warning(f"⚠️ Local LLM Unified統合エラー: {e}")
            self.local_llm_unified = None
        
        # GitHub統合
        try:
            if GITHUB_AVAILABLE:
                import os
                self.github = GitHubIntegration(token=os.getenv("GITHUB_TOKEN"))
                if self.github.is_available():
                    logger.info("✅ GitHub Integration統合完了")
                else:
                    logger.warning("⚠️ GitHub Integrationは利用できません（トークン未設定）")
                    self.github = None
            else:
                self.github = None
        except Exception as e:
            logger.warning(f"⚠️ GitHub Integration統合エラー: {e}")
            self.github = None
        
        # n8n統合
        try:
            if N8N_AVAILABLE:
                import os
                self.n8n = N8NIntegration(
                    base_url=os.getenv("N8N_BASE_URL", "http://localhost:5678"),
                    api_key=os.getenv("N8N_API_KEY")
                )
                if self.n8n.is_available():
                    logger.info("✅ N8N Integration統合完了")
                else:
                    logger.warning("⚠️ N8N Integrationは利用できません（APIキー未設定またはサーバー未起動）")
                    self.n8n = None
            else:
                self.n8n = None
        except Exception as e:
            logger.warning(f"⚠️ N8N Integration統合エラー: {e}")
            self.n8n = None
        
        logger.info("✅ ManaOS Complete Integration初期化完了（ローカルLLM・GitHub・N8N統合済み）")
    
    async def execute_with_full_integration(
        self,
        text: str,
        mode: str = "auto",
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完全統合で実行（人格・記憶・学習・自律・秘書を考慮）
        
        Args:
            text: 入力テキスト
            mode: 実行モード
            user_id: ユーザーID
            context: コンテキスト
        
        Returns:
            実行結果
        """
        start_time = datetime.now()
        
        # 人格を考慮した応答スタイルを取得
        personality_response = None
        if self.personality:
            try:
                personality_response = self.personality.get_personality_response(text, context)
            except Exception as e:
                logger.warning(f"人格応答取得エラー: {e}")
        
        # 記憶から関連情報を検索
        related_memories = []
        if self.rag_memory:
            try:
                related_memories = self.rag_memory.search_memories(text, limit=5)
            except Exception as e:
                logger.warning(f"記憶検索エラー: {e}")
        
        # 学習システムから予測を取得
        predictions = []
        if self.learning_system:
            try:
                predictions = self.learning_system.predict_next_action({
                    "text": text,
                    "mode": mode,
                    "context": context
                })
            except Exception as e:
                logger.warning(f"予測取得エラー: {e}")
        
        # 自律システムで予測的タスクを実行
        autonomous_results = []
        if self.autonomy:
            try:
                autonomous_results = await self.autonomy.predict_and_execute_tasks()
            except Exception as e:
                logger.warning(f"自律タスク実行エラー: {e}")
        
        # Unified Orchestratorで実行
        result = await self.orchestrator.execute(
            text=text,
            mode=mode,
            auto_evaluate=True,
            save_to_memory=True
        )
        
        # 実行時間を計測
        duration = (datetime.now() - start_time).total_seconds()
        
        # メトリクスを記録
        if self.metrics:
            try:
                self.metrics.record_metric(
                    service_name="complete_integration",
                    metric_type=MetricType.RESPONSE_TIME,
                    value=duration
                )
                
                success = result.status == "completed"
                self.metrics.record_metric(
                    service_name="complete_integration",
                    metric_type=MetricType.SUCCESS_RATE,
                    value=1.0 if success else 0.0
                )
            except Exception as e:
                logger.warning(f"メトリクス記録エラー: {e}")
        
        # 学習・記憶に記録
        if self.learning_memory:
            try:
                self.learning_memory.record_and_learn(
                    action="complete_integration_execute",
                    context={
                        "text": text,
                        "mode": mode,
                        "personality": personality_response,
                        "related_memories": len(related_memories),
                        "predictions": len(predictions)
                    },
                    result=result,
                    save_to_memory=True
                )
            except Exception as e:
                logger.warning(f"学習・記憶記録エラー: {e}")
        
        # 秘書システムに報告を追加（重要度が高い場合）
        if self.secretary and result.status == "completed":
            try:
                from secretary_system_optimized import Report
                report = Report(
                    report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    report_type="execution",
                    title=f"実行完了: {text[:50]}",
                    content=json.dumps(result.result or {}, ensure_ascii=False),
                    generated_at=datetime.now().isoformat(),
                    metadata={
                        "duration": duration,
                        "personality": personality_response.get("personality", {}).get("name") if personality_response else None
                    }
                )
                self.secretary.add_report(report)
            except Exception as e:
                logger.warning(f"報告追加エラー: {e}")
        
        return {
            "result": result,
            "personality": personality_response,
            "related_memories": related_memories[:3],  # 上位3件のみ
            "predictions": predictions[:3],  # 上位3件のみ
            "autonomous_results": autonomous_results,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_complete_status(self) -> Dict[str, Any]:
        """完全統合状態を取得"""
        status = {
            "core": {
                "orchestrator": True,
                "status": "operational"
            },
            "memory_learning": {},
            "personality_autonomy_secretary": {},
            "local_llm": {},
            "github": {},
            "n8n": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 記憶系・学習系の状態
        if self.rag_memory:
            try:
                stats = self.rag_memory.get_statistics()
                status["memory_learning"]["rag_memory"] = {
                    "available": True,
                    "total_entries": stats.get("total_entries", 0),
                    "total_importance": stats.get("total_importance", 0)
                }
            except:
                status["memory_learning"]["rag_memory"] = {"available": False}
        
        if self.learning_system:
            try:
                stats = self.learning_system.get_optimization_suggestions()
                status["memory_learning"]["learning_system"] = {
                    "available": True,
                    "total_actions": len(self.learning_system.usage_patterns) if hasattr(self.learning_system, "usage_patterns") else 0
                }
            except:
                status["memory_learning"]["learning_system"] = {"available": False}
        
        if self.learning_memory:
            try:
                stats = self.learning_memory.get_integrated_stats()
                status["memory_learning"]["learning_memory_integration"] = {
                    "available": True,
                    "stats": stats
                }
            except:
                status["memory_learning"]["learning_memory_integration"] = {"available": False}
        
        # 人格系・自律系・秘書系の状態
        if self.pas_integration:
            try:
                pas_status = self.pas_integration.get_integrated_status()
                status["personality_autonomy_secretary"] = pas_status
            except:
                status["personality_autonomy_secretary"] = {"available": False}
        
        # ローカルLLMシステムの状態
        if self.llm_optimization:
            try:
                gpu_status = self.llm_optimization.get_gpu_status()
                status["local_llm"]["llm_optimization"] = {
                    "available": True,
                    "gpu_available": gpu_status.available if gpu_status else False,
                    "models_count": len(self.llm_optimization.models)
                }
            except:
                status["local_llm"]["llm_optimization"] = {"available": False}
        
        if self.local_llm_unified:
            try:
                llm_status = self.local_llm_unified.get_status()
                status["local_llm"]["local_llm_unified"] = {
                    "available": True,
                    "total_systems": llm_status.get("total_systems", 0),
                    "available_systems": llm_status.get("available_systems", [])
                }
            except:
                status["local_llm"]["local_llm_unified"] = {"available": False}
        
        # GitHub統合の状態
        if self.github:
            try:
                status["github"]["github_integration"] = {
                    "available": self.github.is_available(),
                    "token_set": bool(os.getenv("GITHUB_TOKEN"))
                }
            except:
                status["github"]["github_integration"] = {"available": False}
        else:
            status["github"]["github_integration"] = {"available": False, "token_set": False}
        
        # n8n統合の状態
        status["n8n"] = {}
        if self.n8n:
            try:
                workflows = self.n8n.list_workflows()
                status["n8n"]["n8n_integration"] = {
                    "available": self.n8n.is_available(),
                    "api_key_set": bool(os.getenv("N8N_API_KEY")),
                    "base_url": self.n8n.base_url,
                    "workflows_count": len(workflows)
                }
            except:
                status["n8n"]["n8n_integration"] = {"available": False}
        else:
            status["n8n"]["n8n_integration"] = {
                "available": False,
                "api_key_set": bool(os.getenv("N8N_API_KEY")),
                "base_url": os.getenv("N8N_BASE_URL", "http://localhost:5678")
            }
        
        return status
    
    async def optimize_all_systems(self) -> Dict[str, Any]:
        """全システムを最適化"""
        optimizations = {}
        
        # 学習システムの最適化
        if self.learning_system:
            try:
                suggestions = self.learning_system.get_optimization_suggestions()
                optimizations["learning_system"] = suggestions
            except Exception as e:
                logger.warning(f"学習システム最適化エラー: {e}")
        
        # 自律システムの最適化
        if self.autonomy:
            try:
                autonomy_opt = self.autonomy.optimize_autonomy_level()
                optimizations["autonomy_system"] = autonomy_opt
            except Exception as e:
                logger.warning(f"自律システム最適化エラー: {e}")
        
        # PAS統合の最適化
        if self.pas_integration:
            try:
                pas_opt = self.pas_integration.optimize_based_on_learning()
                optimizations["pas_integration"] = pas_opt
            except Exception as e:
                logger.warning(f"PAS統合最適化エラー: {e}")
        
        # ローカルLLMの最適化
        if self.llm_optimization:
            try:
                # GPU状態を取得して最適化提案
                gpu_status = self.llm_optimization.get_gpu_status()
                if gpu_status:
                    optimizations["llm_optimization"] = {
                        "gpu_utilization": gpu_status.utilization,
                        "vram_used": gpu_status.vram_used_gb,
                        "vram_total": gpu_status.vram_total_gb,
                        "recommendation": "GPU使用率が高い場合はモデルのアンロードを検討" if gpu_status.utilization > 80 else "正常"
                    }
            except Exception as e:
                logger.warning(f"LLM最適化エラー: {e}")
        
        # GitHub統合の最適化
        if self.github:
            try:
                if self.github.is_available():
                    optimizations["github"] = {
                        "status": "利用可能",
                        "recommendation": "GitHub統合が正常に動作しています"
                    }
                else:
                    optimizations["github"] = {
                        "status": "トークン未設定",
                        "recommendation": "GITHUB_TOKEN環境変数を設定してください"
                    }
            except Exception as e:
                logger.warning(f"GitHub最適化エラー: {e}")
        
        return {
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("マナOS完全統合システムテスト")
    print("=" * 60)
    
    integration = ManaOSCompleteIntegration()
    
    # 状態を取得
    status = integration.get_complete_status()
    print(f"\n統合状態:")
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

