#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
採点エージェント（Critic）
"""

import os
import httpx
from typing import Dict, Any, List, Optional

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
from .schemas import CritiqueResult, RubricScores, Citation
from .rubric import load_rubric, get_rubric_min_pass_score
from .utils import load_prompt_template, format_prompt, parse_yaml_response
from .critic_guard import CriticGuard

logger = get_service_logger("critic")
error_handler = ManaOSErrorHandler("StepDeepResearchCritic")


class CriticAgent:
    """採点エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Critic設定
        """
        self.config = config
        self.ollama_url = config.get("ollama_url", DEFAULT_OLLAMA_URL)
        self.model = config.get("model", "llama3.2:3b")
        self.min_pass_score = config.get("min_pass_score", 14)
        self.max_iterations = config.get("max_iterations", 3)
        
        # ルーブリック読み込み
        rubric_file = config.get("rubric_file", "step_deep_research/rubric_20_items.yaml")
        self.rubric_data = load_rubric(rubric_file)
        self.min_pass_score = get_rubric_min_pass_score(self.rubric_data)
        
        # プロンプトテンプレート読み込み
        template_path = config.get("critic_prompt_template", "step_deep_research/prompts/critic_prompt.txt")
        # 30項目版がある場合は使用
        if "30" in rubric_file:
            template_path = "step_deep_research/prompts/critic_prompt_v2.txt"
        self.prompt_template = load_prompt_template(template_path)
        
        # Critic Guard初期化
        self.critic_guard = CriticGuard()
    
    def evaluate(self, report: str, iteration: int = 1, citations: Optional[List[Citation]] = None) -> CritiqueResult:
        """
        レポート評価
        
        Args:
            report: レポート内容
            iteration: イテレーション番号
        
        Returns:
            採点結果
        """
        try:
            # ルーブリックをテキスト形式に変換
            rubric_text = self._format_rubric(self.rubric_data)
            
            # プロンプト生成
            prompt = format_prompt(
                self.prompt_template,
                report=report,
                rubric=rubric_text
            )
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # YAMLパース
            critique_data = parse_yaml_response(response)
            
            # CritiqueResultオブジェクトに変換
            critique_result = self._parse_critique(critique_data, iteration)
            
            # Critic Guardで機械的検証
            if citations:
                is_pass_guard, fail_reasons = self.critic_guard.validate_pass_conditions(
                    report=report,
                    citations=citations,
                    critique_result=critique_result
                )
                
                # Guardで不合格なら強制的に不合格
                if not is_pass_guard:
                    critique_result.is_passed = False
                    critique_result.fail_flags.extend(fail_reasons)
                    critique_result.fix_requests.extend([
                        f"【機械的検証】{reason}" for reason in fail_reasons
                    ])
                    logger.warning(f"Critic Guard: 不合格 - {', '.join(fail_reasons)}")
            
            logger.info(f"Critique score: {critique_result.score}/{self.rubric_data.get('rubric', {}).get('total_items', 20)}, Pass: {critique_result.is_passed}")
            return critique_result
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Critique evaluation failed",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.MEDIUM
            )
            # エラー時は最低スコアを返す
            return CritiqueResult(
                score=0,
                is_passed=False,
                fail_flags=["evaluation_error"],
                fix_requests=["評価中にエラーが発生しました。再試行してください。"],
                iteration=iteration
            )
    
    def _format_rubric(self, rubric_data: Dict[str, Any]) -> str:
        """
        ルーブリックをテキスト形式に変換
        
        Args:
            rubric_data: ルーブリックデータ
        
        Returns:
            フォーマット済みテキスト
        """
        rubric = rubric_data.get("rubric", {})
        formatted = []
        
        formatted.append(f"総項目数: {rubric.get('total_items', 20)}")
        formatted.append(f"合格基準: {rubric.get('min_pass_score', 14)}点以上\n")
        
        for category in ["citations", "logic", "practicality", "completeness"]:
            category_data = rubric.get(category, {})
            items = category_data.get("items", [])
            
            if items:
                formatted.append(f"## {category.upper()}")
                for item in items:
                    formatted.append(f"- [{item.get('id')}] {item.get('name')}: {item.get('description')}")
                formatted.append("")
        
        return "\n".join(formatted)
    
    def _parse_critique(self, critique_data: Dict[str, Any], iteration: int) -> CritiqueResult:
        """
        採点データをCritiqueResultオブジェクトに変換
        
        Args:
            critique_data: パースされた採点データ
            iteration: イテレーション番号
        
        Returns:
            CritiqueResultオブジェクト
        """
        score = critique_data.get("score", 0)
        pass_status = critique_data.get("pass", False)
        
        # ルーブリックスコア
        rubric_scores_data = critique_data.get("rubric_scores", {})
        rubric_scores = RubricScores(
            citations=rubric_scores_data.get("citations", {}),
            logic=rubric_scores_data.get("logic", {}),
            practicality=rubric_scores_data.get("practicality", {})
        )
        
        # 失敗フラグ
        fail_flags = critique_data.get("fail_flags", [])
        
        # 修正要求
        fix_requests = critique_data.get("fix_requests", [])
        
        return CritiqueResult(
            score=score,
                is_passed=pass_status,
            rubric_scores=rubric_scores,
            fail_flags=fail_flags,
            fix_requests=fix_requests,
            iteration=iteration
        )
    
    def _call_llm(self, prompt: str) -> str:
        """LLMを呼び出す"""
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 3000
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
                severity=ErrorSeverity.MEDIUM
            )
            raise

