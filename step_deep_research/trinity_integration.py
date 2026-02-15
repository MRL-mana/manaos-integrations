#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trinity System統合
レミ/ルナ/ミナへの役割分担実装
"""

from typing import Dict, Any, Optional
from enum import Enum

from manaos_logger import get_logger
from .schemas import Plan, ResearchResults, CritiqueResult

logger = get_service_logger("trinity-integration")


class TrinityAgent(str, Enum):
    """Trinity System エージェント"""
    REMI = "remi"  # 判断・実行
    LUNA = "luna"  # 監視・分析
    MINA = "mina"  # 記憶・学習


class TrinityIntegration:
    """Trinity System統合"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Trinity統合設定
        """
        self.config = config
        trinity_config = config.get("trinity_integration", {})
        
        self.remi_roles = trinity_config.get("remi_role", ["planner", "writer"])
        self.luna_roles = trinity_config.get("luna_role", ["searcher", "reader"])
        self.mina_roles = trinity_config.get("mina_role", ["verifier", "critic_assistant"])
        
        logger.info(f"Trinity統合初期化: Remi={self.remi_roles}, Luna={self.luna_roles}, Mina={self.mina_roles}")
    
    def route_to_agent(self, task_type: str) -> Optional[TrinityAgent]:
        """
        タスクタイプからエージェントにルーティング
        
        Args:
            task_type: タスクタイプ（planner, searcher, reader, verifier, writer, critic）
        
        Returns:
            担当エージェント（Noneの場合はデフォルト）
        """
        if task_type in self.remi_roles:
            return TrinityAgent.REMI
        elif task_type in self.luna_roles:
            return TrinityAgent.LUNA
        elif task_type in self.mina_roles:
            return TrinityAgent.MINA
        
        return None
    
    def get_agent_for_planning(self) -> TrinityAgent:
        """計画作成はRemi担当"""
        return TrinityAgent.REMI
    
    def get_agent_for_search(self) -> TrinityAgent:
        """検索はLuna担当"""
        return TrinityAgent.LUNA
    
    def get_agent_for_reading(self) -> TrinityAgent:
        """要点抽出はLuna担当"""
        return TrinityAgent.LUNA
    
    def get_agent_for_verification(self) -> TrinityAgent:
        """検証はMina担当"""
        return TrinityAgent.MINA
    
    def get_agent_for_writing(self) -> TrinityAgent:
        """報告書作成はRemi担当"""
        return TrinityAgent.REMI
    
    def get_agent_for_critique(self) -> TrinityAgent:
        """採点はMina補助"""
        return TrinityAgent.MINA
    
    def format_agent_context(self, agent: TrinityAgent, context: Dict[str, Any]) -> str:
        """
        エージェント用のコンテキストをフォーマット
        
        Args:
            agent: エージェント
            context: コンテキストデータ
        
        Returns:
            フォーマット済みコンテキスト
        """
        if agent == TrinityAgent.REMI:
            return self._format_remi_context(context)
        elif agent == TrinityAgent.LUNA:
            return self._format_luna_context(context)
        elif agent == TrinityAgent.MINA:
            return self._format_mina_context(context)
        
        return ""
    
    def _format_remi_context(self, context: Dict[str, Any]) -> str:
        """Remi用コンテキスト（判断・実行）"""
        formatted = []
        formatted.append("【Remi（判断・実行）の役割】")
        formatted.append("- 計画作成と報告書執筆を担当")
        formatted.append("- 実装可能な形で出力する")
        
        if "plan" in context:
            plan: Plan = context["plan"]
            formatted.append(f"\n現在の計画: {plan.goal}")
            formatted.append(f"タスク数: {len(plan.todo)}")
        
        return "\n".join(formatted)
    
    def _format_luna_context(self, context: Dict[str, Any]) -> str:
        """Luna用コンテキスト（監視・分析）"""
        formatted = []
        formatted.append("【Luna（監視・分析）の役割】")
        formatted.append("- 情報収集と要点抽出を担当")
        formatted.append("- データの質と量を監視")
        
        if "research_results" in context:
            results: ResearchResults = context["research_results"]
            formatted.append(f"\n収集済み情報:")
            formatted.append(f"- 引用: {len(results.citations)}件")
            formatted.append(f"- 要約: {len(results.summaries)}件")
            formatted.append(f"- 矛盾: {len(results.contradictions)}件")
        
        return "\n".join(formatted)
    
    def _format_mina_context(self, context: Dict[str, Any]) -> str:
        """Mina用コンテキスト（記憶・学習）"""
        formatted = []
        formatted.append("【Mina（記憶・学習）の役割】")
        formatted.append("- 検証と採点補助を担当")
        formatted.append("- 過去の成功パターンを参照")
        
        if "critique_result" in context:
            critique: CritiqueResult = context["critique_result"]
            formatted.append(f"\n採点結果:")
            formatted.append(f"- スコア: {critique.score}/30")
            formatted.append(f"- 合格: {'✅' if critique.is_passed else '❌'}")
            if critique.fail_flags:
                formatted.append(f"- 失敗フラグ: {', '.join(critique.fail_flags)}")
        
        return "\n".join(formatted)
    
    def enhance_prompt_for_agent(self, prompt: str, agent: TrinityAgent, context: Dict[str, Any] = None) -> str:
        """
        エージェント用にプロンプトを強化
        
        Args:
            prompt: 元のプロンプト
            agent: エージェント
            context: コンテキスト
        
        Returns:
            強化されたプロンプト
        """
        agent_context = self.format_agent_context(agent, context or {})
        
        enhanced = f"""{agent_context}

---

{prompt}
"""
        return enhanced
    
    def log_agent_activity(self, agent: TrinityAgent, activity: str, details: Dict[str, Any] = None):
        """
        エージェントの活動をログに記録
        
        Args:
            agent: エージェント
            activity: 活動内容
            details: 詳細情報
        """
        log_msg = f"[{agent.value.upper()}] {activity}"
        if details:
            log_msg += f" | {details}"
        logger.info(log_msg)



