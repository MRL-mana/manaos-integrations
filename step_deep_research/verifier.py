#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検証エージェント（Verifier）
"""

import httpx
from typing import Dict, Any, List

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import (
    Contradiction, CounterArgument, ReliabilityAssessment,
    Citation, Summary, ContradictionType, ContradictionSeverity, ReliabilityLevel
)
from .utils import load_prompt_template, format_prompt, parse_json_response

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchVerifier")


class Verifier:
    """検証エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Verifier設定
        """
        self.config = config
        self.ollama_url = config.get("ollama_url", "http://127.0.0.1:11434")
        self.model = config.get("model", "llama3.2:3b")
        self.contradiction_threshold = config.get("contradiction_threshold", 0.7)
        
        # プロンプトテンプレート読み込み
        template_path = config.get("verification_prompt_template", "step_deep_research/prompts/verifier_prompt.txt")
        self.prompt_template = load_prompt_template(template_path)
    
    def check_contradictions(
        self,
        citations: List[Citation],
        summaries: List[Summary]
    ) -> List[Contradiction]:
        """
        矛盾をチェック
        
        Args:
            citations: 引用リスト
            summaries: 要約リスト
        
        Returns:
            矛盾リスト
        """
        try:
            # プロンプト生成
            citations_text = self._format_citations(citations)
            summaries_text = self._format_summaries(summaries)
            
            prompt = format_prompt(
                self.prompt_template,
                citations=citations_text,
                summaries=summaries_text
            )
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # JSONパース
            data = parse_json_response(response)
            
            # Contradictionオブジェクトに変換
            contradictions = []
            for contra_data in data.get("contradictions", []):
                contradiction = Contradiction(
                    type=ContradictionType(contra_data.get("type", "indirect")),
                    source1=contra_data.get("source1", ""),
                    source2=contra_data.get("source2", ""),
                    description=contra_data.get("description", ""),
                    severity=ContradictionSeverity(contra_data.get("severity", "medium"))
                )
                contradictions.append(contradiction)
            
            logger.info(f"Found {len(contradictions)} contradictions")
            return contradictions
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Contradiction check failed",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.MEDIUM
            )
            return []
    
    def find_counter_arguments(
        self,
        citations: List[Citation],
        summaries: List[Summary]
    ) -> List[CounterArgument]:
        """
        反証候補を探す
        
        Args:
            citations: 引用リスト
            summaries: 要約リスト
        
        Returns:
            反証候補リスト
        """
        try:
            # プロンプト生成
            citations_text = self._format_citations(citations)
            summaries_text = self._format_summaries(summaries)
            
            prompt = format_prompt(
                self.prompt_template,
                citations=citations_text,
                summaries=summaries_text
            )
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # JSONパース
            data = parse_json_response(response)
            
            # CounterArgumentオブジェクトに変換
            counter_arguments = []
            for counter_data in data.get("counter_arguments", []):
                counter_arg = CounterArgument(
                    claim=counter_data.get("claim", ""),
                    counter_evidence=counter_data.get("counter_evidence", ""),
                    source=counter_data.get("source", "")
                )
                counter_arguments.append(counter_arg)
            
            logger.info(f"Found {len(counter_arguments)} counter arguments")
            return counter_arguments
            
        except Exception as e:
            logger.warning(f"Counter argument search failed: {e}")
            return []
    
    def assess_reliability(
        self,
        citations: List[Citation]
    ) -> List[ReliabilityAssessment]:
        """
        信頼性を評価
        
        Args:
            citations: 引用リスト
        
        Returns:
            信頼性評価リスト
        """
        try:
            # プロンプト生成
            citations_text = self._format_citations(citations)
            summaries_text = ""  # 要約は不要
            
            prompt = format_prompt(
                self.prompt_template,
                citations=citations_text,
                summaries=summaries_text
            )
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # JSONパース
            data = parse_json_response(response)
            
            # ReliabilityAssessmentオブジェクトに変換
            assessments = []
            for assess_data in data.get("reliability_assessment", []):
                assessment = ReliabilityAssessment(
                    source=assess_data.get("source", ""),
                    reliability=ReliabilityLevel(assess_data.get("reliability", "medium")),
                    reason=assess_data.get("reason", "")
                )
                assessments.append(assessment)
            
            logger.info(f"Assessed reliability for {len(assessments)} sources")
            return assessments
            
        except Exception as e:
            logger.warning(f"Reliability assessment failed: {e}")
            return []
    
    def _format_citations(self, citations: List[Citation]) -> str:
        """引用をテキスト形式にフォーマット"""
        formatted = []
        for i, citation in enumerate(citations, 1):
            formatted.append(f"""
[{i}] {citation.id}
Source: {citation.source}
Quote: {citation.quote}
Summary: {citation.summary}
Tag: {citation.tag.value}
Relevance: {citation.relevance_score}
""")
        return "\n".join(formatted)
    
    def _format_summaries(self, summaries: List[Summary]) -> str:
        """要約をテキスト形式にフォーマット"""
        formatted = []
        for i, summary in enumerate(summaries, 1):
            formatted.append(f"""
[{i}] {summary.source}
Summary: {summary.summary}
Key Points: {', '.join(summary.key_points)}
""")
        return "\n".join(formatted)
    
    def _call_llm(self, prompt: str) -> str:
        """LLMを呼び出す"""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
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
                severity=ErrorSeverity.MEDIUM
            )
            raise



