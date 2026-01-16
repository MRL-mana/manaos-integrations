#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 OH MY OPENCODE × Trinity System 統合ブリッジ
Remi（判断）/ Luna（監視）/ Mina（記憶）との統合
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("OHMyOpenCodeTrinityBridge")
timeout_config = get_timeout_config()


@dataclass
class RemiAnalysis:
    """Remi（判断）の分析結果"""
    task_priority: str  # "low", "medium", "high", "critical"
    estimated_time: int  # 推定実行時間（秒）
    complexity: str  # "simple", "medium", "complex", "very_complex"
    recommended_mode: str  # "normal" or "ultra_work"
    risk_assessment: str  # リスク評価
    suggestions: List[str]  # 推奨事項
    confidence: float  # 信頼度（0.0-1.0)


@dataclass
class LunaMonitoring:
    """Luna（監視）の監視設定"""
    monitoring_enabled: bool
    check_interval: int  # チェック間隔（秒）
    failure_threshold: int  # 失敗閾値
    alert_on_error: bool
    metrics_to_track: List[str]  # 追跡するメトリクス


@dataclass
class MinaMemory:
    """Mina（記憶）の記憶情報"""
    similar_tasks: List[Dict[str, Any]]  # 類似タスク
    learned_patterns: List[Dict[str, Any]]  # 学習されたパターン
    relevant_knowledge: List[Dict[str, Any]]  # 関連知識
    success_rate: Optional[float]  # 類似タスクの成功率


class TrinityBridge:
    """Trinity System統合ブリッジ"""
    
    def __init__(
        self,
        intent_router_url: str = "http://localhost:5100",
        task_planner_url: str = "http://localhost:5101",
        task_critic_url: str = "http://localhost:5102",
        rag_memory_url: str = "http://localhost:5103",
        learning_system_url: str = "http://localhost:5126",
        orchestrator_url: str = "http://localhost:5106"
    ):
        """
        初期化
        
        Args:
            intent_router_url: Intent Router API URL
            task_planner_url: Task Planner API URL
            task_critic_url: Task Critic API URL
            rag_memory_url: RAG Memory API URL
            learning_system_url: Learning System API URL
            orchestrator_url: Unified Orchestrator API URL
        """
        self.intent_router_url = intent_router_url
        self.task_planner_url = task_planner_url
        self.task_critic_url = task_critic_url
        self.rag_memory_url = rag_memory_url
        self.learning_system_url = learning_system_url
        self.orchestrator_url = orchestrator_url
        
        # HTTPクライアント
        self.http_client = httpx.AsyncClient(timeout=timeout_config.get("api_call", 5.0))
        
        logger.info("✅ Trinity Bridge initialized")
    
    async def remi_analyze(
        self,
        task_description: str,
        task_type: str = "general"
    ) -> RemiAnalysis:
        """
        Remi（判断）でタスクを分析
        
        Args:
            task_description: タスクの説明
            task_type: タスクタイプ
        
        Returns:
            Remi分析結果
        """
        try:
            # Intent Routerで意図分類
            intent_result = await self._classify_intent(task_description)
            intent_type = intent_result.get("intent_type", "general")
            confidence = intent_result.get("confidence", 0.5)
            
            # Task Plannerで計画作成（推定時間の取得）
            plan_result = await self._create_plan(task_description, intent_type)
            estimated_time = plan_result.get("estimated_time", 300)
            complexity = plan_result.get("complexity", "medium")
            
            # 優先度の決定
            priority = self._determine_priority(intent_type, complexity, confidence)
            
            # 推奨モードの決定
            recommended_mode = self._determine_recommended_mode(
                task_type, complexity, estimated_time
            )
            
            # リスク評価
            risk_assessment = self._assess_risk(complexity, estimated_time, confidence)
            
            # 推奨事項
            suggestions = self._generate_suggestions(
                task_type, complexity, recommended_mode
            )
            
            return RemiAnalysis(
                task_priority=priority,
                estimated_time=estimated_time,
                complexity=complexity,
                recommended_mode=recommended_mode,
                risk_assessment=risk_assessment,
                suggestions=suggestions,
                confidence=confidence
            )
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"task_description": task_description[:100]},
                user_message="Remi分析に失敗しました"
            )
            logger.warning(f"Remi分析エラー: {error.message}")
            
            # デフォルト値を返す
            return RemiAnalysis(
                task_priority="medium",
                estimated_time=300,
                complexity="medium",
                recommended_mode="normal",
                risk_assessment="medium",
                suggestions=[],
                confidence=0.5
            )
    
    async def luna_monitor(
        self,
        task_description: str,
        task_id: str,
        estimated_time: int = 300
    ) -> LunaMonitoring:
        """
        Luna（監視）で監視設定
        
        Args:
            task_description: タスクの説明
            task_id: タスクID
            estimated_time: 推定実行時間（秒）
        
        Returns:
            Luna監視設定
        """
        try:
            # 推定時間に基づいてチェック間隔を決定
            check_interval = min(60, max(10, estimated_time // 10))
            
            # 失敗閾値を決定
            failure_threshold = max(3, estimated_time // 100)
            
            # 追跡するメトリクス
            metrics_to_track = [
                "execution_time",
                "cost",
                "iterations",
                "errors",
                "success_rate"
            ]
            
            return LunaMonitoring(
                monitoring_enabled=True,
                check_interval=check_interval,
                failure_threshold=failure_threshold,
                alert_on_error=True,
                metrics_to_track=metrics_to_track
            )
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"task_id": task_id},
                user_message="Luna監視設定に失敗しました"
            )
            logger.warning(f"Luna監視設定エラー: {error.message}")
            
            # デフォルト値を返す
            return LunaMonitoring(
                monitoring_enabled=True,
                check_interval=60,
                failure_threshold=3,
                alert_on_error=True,
                metrics_to_track=["execution_time", "cost", "errors"]
            )
    
    async def mina_search(
        self,
        task_description: str,
        task_type: str = "general",
        limit: int = 5
    ) -> MinaMemory:
        """
        Mina（記憶）で類似タスクを検索
        
        Args:
            task_description: タスクの説明
            task_type: タスクタイプ
            limit: 検索結果の最大数
        
        Returns:
            Mina記憶情報
        """
        try:
            similar_tasks = []
            learned_patterns = []
            relevant_knowledge = []
            success_rate = None
            
            # RAG Memoryで類似タスクを検索
            try:
                rag_result = await self._search_rag_memory(task_description, limit)
                similar_tasks = rag_result.get("results", [])
            except Exception as e:
                logger.debug(f"RAG Memory検索エラー（無視）: {e}")
            
            # Learning Systemで学習パターンを取得
            try:
                learning_result = await self._get_learned_patterns(task_type, limit)
                learned_patterns = learning_result.get("patterns", [])
                success_rate = learning_result.get("success_rate")
            except Exception as e:
                logger.debug(f"Learning System検索エラー（無視）: {e}")
            
            # 関連知識を取得
            try:
                knowledge_result = await self._get_relevant_knowledge(
                    task_description, limit
                )
                relevant_knowledge = knowledge_result.get("knowledge", [])
            except Exception as e:
                logger.debug(f"関連知識取得エラー（無視）: {e}")
            
            return MinaMemory(
                similar_tasks=similar_tasks,
                learned_patterns=learned_patterns,
                relevant_knowledge=relevant_knowledge,
                success_rate=success_rate
            )
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"task_description": task_description[:100]},
                user_message="Mina検索に失敗しました"
            )
            logger.warning(f"Mina検索エラー: {error.message}")
            
            # デフォルト値を返す
            return MinaMemory(
                similar_tasks=[],
                learned_patterns=[],
                relevant_knowledge=[],
                success_rate=None
            )
    
    async def _classify_intent(self, text: str) -> Dict[str, Any]:
        """意図分類"""
        try:
            response = await self.http_client.post(
                f"{self.intent_router_url}/api/classify",
                json={"text": text}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Intent Router呼び出しエラー: {e}")
            return {"intent_type": "general", "confidence": 0.5}
    
    async def _create_plan(self, task_description: str, intent_type: str) -> Dict[str, Any]:
        """計画作成"""
        try:
            response = await self.http_client.post(
                f"{self.task_planner_url}/api/plan",
                json={
                    "text": task_description,
                    "intent_type": intent_type
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Task Planner呼び出しエラー: {e}")
            return {"estimated_time": 300, "complexity": "medium"}
    
    async def _search_rag_memory(self, query: str, limit: int) -> Dict[str, Any]:
        """RAG Memory検索"""
        try:
            response = await self.http_client.get(
                f"{self.rag_memory_url}/api/search",
                params={"query": query, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"RAG Memory呼び出しエラー: {e}")
            return {"results": []}
    
    async def _get_learned_patterns(self, task_type: str, limit: int) -> Dict[str, Any]:
        """学習パターン取得"""
        try:
            response = await self.http_client.get(
                f"{self.learning_system_url}/api/analyze",
                params={"task_type": task_type, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Learning System呼び出しエラー: {e}")
            return {"patterns": [], "success_rate": None}
    
    async def _get_relevant_knowledge(self, query: str, limit: int) -> Dict[str, Any]:
        """関連知識取得"""
        try:
            # Byterover MCP経由で知識を取得（実装予定）
            # 現在は空の結果を返す
            return {"knowledge": []}
        except Exception as e:
            logger.debug(f"関連知識取得エラー: {e}")
            return {"knowledge": []}
    
    def _determine_priority(
        self,
        intent_type: str,
        complexity: str,
        confidence: float
    ) -> str:
        """優先度を決定"""
        # 複雑度と信頼度に基づいて優先度を決定
        if complexity == "very_complex" and confidence > 0.8:
            return "critical"
        elif complexity == "complex" or confidence > 0.7:
            return "high"
        elif complexity == "medium":
            return "medium"
        else:
            return "low"
    
    def _determine_recommended_mode(
        self,
        task_type: str,
        complexity: str,
        estimated_time: int
    ) -> str:
        """推奨モードを決定"""
        # Ultra Workモードが推奨される条件
        ultra_work_types = ["specification", "complex_bug", "architecture_design"]
        
        if task_type in ultra_work_types:
            return "ultra_work"
        elif complexity == "very_complex" and estimated_time > 1800:
            return "ultra_work"
        else:
            return "normal"
    
    def _assess_risk(
        self,
        complexity: str,
        estimated_time: int,
        confidence: float
    ) -> str:
        """リスク評価"""
        if complexity == "very_complex" and confidence < 0.5:
            return "high"
        elif complexity == "complex" and estimated_time > 3600:
            return "medium_high"
        elif confidence < 0.3:
            return "medium"
        else:
            return "low"
    
    def _generate_suggestions(
        self,
        task_type: str,
        complexity: str,
        recommended_mode: str
    ) -> List[str]:
        """推奨事項を生成"""
        suggestions = []
        
        if recommended_mode == "ultra_work":
            suggestions.append("Ultra Workモードを使用することを推奨します")
        
        if complexity == "very_complex":
            suggestions.append("タスクを小さなステップに分割することを推奨します")
        
        if task_type == "complex_bug":
            suggestions.append("デバッグログを有効にすることを推奨します")
        
        return suggestions
    
    async def close(self):
        """リソースを解放"""
        await self.http_client.aclose()


# 使用例
if __name__ == "__main__":
    async def main():
        bridge = TrinityBridge()
        
        # Remi分析
        remi_analysis = await bridge.remi_analyze(
            "PythonでREST APIを作成してください",
            task_type="code_generation"
        )
        print(f"Remi分析: {asdict(remi_analysis)}")
        
        # Luna監視設定
        luna_monitoring = await bridge.luna_monitor(
            "PythonでREST APIを作成してください",
            task_id="test_task_1",
            estimated_time=600
        )
        print(f"Luna監視: {asdict(luna_monitoring)}")
        
        # Mina検索
        mina_memory = await bridge.mina_search(
            "PythonでREST APIを作成してください",
            task_type="code_generation"
        )
        print(f"Mina記憶: {asdict(mina_memory)}")
        
        await bridge.close()
    
    asyncio.run(main())
