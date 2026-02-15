#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
要点抽出エージェント（Reader）
"""

import httpx
from typing import Dict, Any, List
from datetime import datetime

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import Citation, Summary, CitationTag, SearchResult
from .utils import load_prompt_template, format_prompt, parse_json_response
from .source_quality_filter import SourceQualityFilter, SourceQuality

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchReader")


class Reader:
    """要点抽出エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Reader設定
        """
        self.config = config
        self.ollama_url = config.get("ollama_url", "http://127.0.0.1:11434")
        self.model = config.get("model", "llama3.2:3b")
        self.max_chunk_size = config.get("max_chunk_size", 2000)
        
        # プロンプトテンプレート読み込み
        template_path = config.get("extraction_prompt_template", "step_deep_research/prompts/reader_prompt.txt")
        self.prompt_template = load_prompt_template(template_path)
        
        # ソース品質フィルタ初期化
        self.quality_filter = SourceQualityFilter()
    
    def extract_citations(self, search_results: List[SearchResult]) -> List[Citation]:
        """
        引用を抽出
        
        Args:
            search_results: 検索結果リスト
        
        Returns:
            引用リスト
        """
        citations = []
        
        for result in search_results:
            try:
                # プロンプト生成
                search_results_text = self._format_search_results([result])
                prompt = format_prompt(
                    self.prompt_template,
                    search_results=search_results_text
                )
                
                # LLM呼び出し
                response = self._call_llm(prompt)
                
                # JSONパース
                data = parse_json_response(response)
                
                # Citationオブジェクトに変換
                for cite_data in data.get("citations", []):
                    citation = Citation(
                        id=cite_data.get("id", f"cite_{len(citations) + 1}"),
                        source=cite_data.get("source", result.url),
                        quote=cite_data.get("quote", ""),
                        summary=cite_data.get("summary", ""),
                        tag=CitationTag(cite_data.get("tag", "fact")),
                        relevance_score=cite_data.get("relevance_score", 0.5)
                    )
                    citations.append(citation)
                    
            except Exception as e:
                logger.warning(f"Citation extraction failed for {result.url}: {e}")
                continue
        
            logger.info(f"Extracted {len(citations)} citations")
        
        # 品質フィルタ適用（低品質を除外）
        filtered_citations = self.quality_filter.filter_citations_by_quality(
            citations,
            min_quality=SourceQuality.TERTIARY  # 最低でも三次情報以上
        )
        
        # 品質警告を追加
        filtered_citations = self.quality_filter.add_quality_warnings(filtered_citations)
        
        logger.info(f"Filtered citations: {len(filtered_citations)}/{len(citations)}")
        return filtered_citations
    
    def create_summaries(self, search_results: List[SearchResult]) -> List[Summary]:
        """
        要約を作成
        
        Args:
            search_results: 検索結果リスト
        
        Returns:
            要約リスト
        """
        summaries = []
        
        # チャンクに分割（長すぎる場合は分割）
        chunks = self._chunk_results(search_results)
        
        for chunk in chunks:
            try:
                # プロンプト生成
                search_results_text = self._format_search_results(chunk)
                prompt = format_prompt(
                    self.prompt_template,
                    search_results=search_results_text
                )
                
                # LLM呼び出し
                response = self._call_llm(prompt)
                
                # JSONパース
                data = parse_json_response(response)
                
                # Summaryオブジェクトに変換
                for summary_data in data.get("summaries", []):
                    summary = Summary(
                        source=summary_data.get("source", ""),
                        summary=summary_data.get("summary", ""),
                        key_points=summary_data.get("key_points", [])
                    )
                    summaries.append(summary)
                    
            except Exception as e:
                logger.warning(f"Summary creation failed: {e}")
                continue
        
        logger.info(f"Created {len(summaries)} summaries")
        return summaries
    
    def _format_search_results(self, results: List[SearchResult]) -> str:
        """
        検索結果をテキスト形式にフォーマット
        
        Args:
            results: 検索結果リスト
        
        Returns:
            フォーマット済みテキスト
        """
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"""
[{i}] {result.title}
URL: {result.url}
Content: {result.snippet}
Source: {result.source}
""")
        return "\n".join(formatted)
    
    def _chunk_results(self, results: List[SearchResult]) -> List[List[SearchResult]]:
        """
        検索結果をチャンクに分割
        
        Args:
            results: 検索結果リスト
        
        Returns:
            チャンクのリスト
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for result in results:
            result_size = len(result.title) + len(result.snippet)
            if current_size + result_size > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [result]
                current_size = result_size
            else:
                current_chunk.append(result)
                current_size += result_size
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
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
                            "temperature": 0.2,
                            "num_predict": 1500
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


