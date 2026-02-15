#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
計画作成エージェント（Planner）
"""

import os
import httpx
from typing import Dict, Any
from pathlib import Path

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import Plan, SuccessCriterion, TodoItem, Risk, TaskTool, TaskPriority
from .utils import load_prompt_template, format_prompt, parse_yaml_response

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchPlanner")


class PlannerAgent:
    """計画作成エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Planner設定
        """
        self.config = config
        self.ollama_url = config.get("ollama_url", DEFAULT_OLLAMA_URL)
        self.model = config.get("model", "llama3.2:3b")
        self.max_todo_items = config.get("max_todo_items", 15)
        
        # プロンプトテンプレート読み込み
        template_path = config.get("planning_prompt_template", "step_deep_research/prompts/planner_prompt.txt")
        self.prompt_template = load_prompt_template(template_path)
    
    def create_plan(self, user_query: str) -> Plan:
        """
        調査計画作成
        
        Args:
            user_query: ユーザーの調査依頼
        
        Returns:
            調査計画
        """
        try:
            # プロンプト生成
            prompt = format_prompt(self.prompt_template, user_query=user_query)
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # YAMLパース
            plan_data = parse_yaml_response(response)
            
            # Planオブジェクトに変換
            plan = self._parse_plan(plan_data)
            
            logger.info(f"Plan created: {len(plan.todo)} tasks")
            return plan
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Failed to create plan",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH
            )
            raise
    
    def _call_llm(self, prompt: str) -> str:
        """
        LLMを呼び出す
        
        Args:
            prompt: プロンプト
        
        Returns:
            LLMのレスポンス
        """
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 2000
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.HTTPError as e:
            error_handler.handle_error(
                e,
                "LLM API call failed",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH
            )
            raise
    
    def _parse_plan(self, plan_data: Dict[str, Any]) -> Plan:
        """
        計画データをPlanオブジェクトに変換
        
        Args:
            plan_data: パースされた計画データ
        
        Returns:
            Planオブジェクト
        """
        # 成功条件
        success_criteria = []
        for criterion_data in plan_data.get("success_criteria", []):
            criterion = SuccessCriterion(
                criterion=criterion_data.get("criterion", ""),
                priority=TaskPriority(criterion_data.get("priority", "medium")),
                measurable=criterion_data.get("measurable", True)
            )
            success_criteria.append(criterion)
        
        # タスクリスト
        todo_items = []
        for todo_data in plan_data.get("todo", [])[:self.max_todo_items]:
            todo_item = TodoItem(
                step=todo_data.get("step", len(todo_items) + 1),
                description=todo_data.get("description", ""),
                tool=TaskTool(todo_data.get("tool", "none")),
                expected_output=todo_data.get("expected_output", ""),
                dependencies=todo_data.get("dependencies", []),
                priority=TaskPriority(todo_data.get("priority", "medium"))
            )
            todo_items.append(todo_item)
        
        # リスク
        risks = []
        for risk_data in plan_data.get("risks", []):
            risk = Risk(
                risk=risk_data.get("risk", ""),
                mitigation=risk_data.get("mitigation", "")
            )
            risks.append(risk)
        
        # Planオブジェクト作成
        plan = Plan(
            goal=plan_data.get("goal", ""),
            success_criteria=success_criteria,
            todo=todo_items,
            risks=risks,
            estimated_time_minutes=plan_data.get("estimated_time_minutes", 60),
            estimated_cost_tokens=plan_data.get("estimated_cost_tokens", 30000)
        )
        
        return plan



