#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearXNG + ローカルLLM統合モジュール
ローカルLLMや学習系でSearXNG検索を使えるようにする
"""

import os
from typing import Optional, Dict, List, Any
from pathlib import Path

from searxng_integration import SearXNGIntegration

# LangChain統合（オプション）
try:
    from langchain.tools import Tool
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None

# Ollama統合（オプション）
try:
    from langchain_community.llms import Ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    Ollama = None


class SearXNGLLMIntegration:
    """SearXNG + ローカルLLM統合クラス"""
    
    def __init__(
        self,
        searxng_url: Optional[str] = None,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b"
    ):
        """
        初期化
        
        Args:
            searxng_url: SearXNGサーバーのURL
            ollama_url: OllamaサーバーのURL
            model_name: 使用するLLMモデル名
        """
        self.searxng = SearXNGIntegration(base_url=searxng_url)
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.llm = None
        self.search_tool = None
        
        if LANGCHAIN_AVAILABLE and OLLAMA_AVAILABLE:
            self._initialize_llm()
            self._create_search_tool()
    
    def _initialize_llm(self):
        """LLMを初期化"""
        try:
            self.llm = Ollama(
                base_url=self.ollama_url,
                model=self.model_name,
                temperature=0.7
            )
        except Exception as e:
            print(f"LLM初期化エラー: {e}")
            self.llm = None
    
    def _create_search_tool(self):
        """検索ツールを作成"""
        def search_web(query: str) -> str:
            """Web検索を実行"""
            result = self.searxng.search(query, max_results=5)
            if result.get("error"):
                return f"検索エラー: {result['error']}"
            
            # 結果を整形
            output = f"検索クエリ: {result.get('query', '')}\n"
            output += f"結果数: {result.get('count', 0)}件\n\n"
            
            for i, item in enumerate(result.get("results", []), 1):
                output += f"{i}. {item.get('title', '')}\n"
                output += f"   URL: {item.get('url', '')}\n"
                if item.get('content'):
                    content = item.get('content', '')[:200]
                    output += f"   概要: {content}...\n"
                output += "\n"
            
            return output
        
        if Tool:
            self.search_tool = Tool(
                name="web_search",
                description="Web検索を実行します。最新情報や事実確認が必要な場合に使用してください。",
                func=search_web
            )
    
    def search_with_llm(
        self,
        query: str,
        use_llm: bool = True,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        LLMを使って検索結果を要約・分析
        
        Args:
            query: 検索クエリ
            use_llm: LLMを使って要約するか
            max_results: 最大結果数
        
        Returns:
            検索結果とLLM要約を含む辞書
        """
        # 検索実行
        search_result = self.searxng.search(query, max_results=max_results)
        
        if search_result.get("error"):
            return search_result
        
        if not use_llm or not self.llm:
            return search_result
        
        # LLMで要約
        try:
            # 検索結果をテキストに変換
            results_text = ""
            for item in search_result.get("results", []):
                results_text += f"タイトル: {item.get('title', '')}\n"
                results_text += f"URL: {item.get('url', '')}\n"
                if item.get('content'):
                    results_text += f"内容: {item.get('content', '')}\n"
                results_text += "\n"
            
            # LLMに要約を依頼
            prompt = f"""以下のWeb検索結果を要約し、重要な情報を整理してください。

検索クエリ: {query}

検索結果:
{results_text}

要約（日本語で、重要なポイントを箇条書きで）:"""
            
            summary = self.llm.invoke(prompt)
            
            search_result["llm_summary"] = summary
            search_result["has_llm_summary"] = True
            
        except Exception as e:
            search_result["llm_summary"] = f"要約生成エラー: {e}"
            search_result["has_llm_summary"] = False
        
        return search_result
    
    def get_langchain_tool(self) -> Optional[Any]:
        """
        LangChainツールを取得
        
        Returns:
            LangChain Toolオブジェクト（利用可能な場合）
        """
        return self.search_tool
    
    def create_rag_context(
        self,
        query: str,
        max_results: int = 5,
        include_urls: bool = True
    ) -> str:
        """
        RAG用のコンテキストを生成（検索結果をRAGに使える形式に）
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
            include_urls: URLを含めるか
        
        Returns:
            RAG用コンテキスト文字列
        """
        result = self.searxng.search(query, max_results=max_results)
        
        if result.get("error"):
            return f"検索エラー: {result['error']}"
        
        context_parts = [f"検索クエリ: {query}\n"]
        
        for i, item in enumerate(result.get("results", []), 1):
            context_parts.append(f"[{i}] {item.get('title', '')}")
            if include_urls:
                context_parts.append(f"URL: {item.get('url', '')}")
            if item.get('content'):
                context_parts.append(f"内容: {item.get('content', '')}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def collect_training_data(
        self,
        queries: List[str],
        output_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        学習データを収集（検索結果を学習データとして保存）
        
        Args:
            queries: 検索クエリのリスト
            output_file: 出力ファイルパス（JSON形式）
        
        Returns:
            収集したデータのリスト
        """
        training_data = []
        
        for query in queries:
            result = self.searxng.search(query, max_results=5)
            
            if not result.get("error"):
                training_data.append({
                    "query": query,
                    "results": result.get("results", []),
                    "timestamp": result.get("timestamp")
                })
        
        # ファイルに保存
        if output_file:
            import json
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        return training_data


def create_searxng_tool_for_ollama(
    searxng_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ollama用の関数呼び出しツール定義を返す
    
    Args:
        searxng_url: SearXNGサーバーのURL
    
    Returns:
        Ollama関数呼び出し用のツール定義
    """
    searxng = SearXNGIntegration(base_url=searxng_url)
    
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Web検索を実行します。最新情報や事実確認が必要な場合に使用してください。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "検索クエリ"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大結果数（デフォルト: 5）",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }


def search_for_ollama(query: str, max_results: int = 5) -> str:
    """
    Ollamaから呼び出される検索関数
    
    Args:
        query: 検索クエリ
        max_results: 最大結果数
    
    Returns:
        検索結果の文字列
    """
    searxng = SearXNGIntegration()
    result = searxng.search(query, max_results=max_results)
    
    if result.get("error"):
        return f"検索エラー: {result['error']}"
    
    output = f"検索クエリ: {result.get('query', '')}\n"
    output += f"結果数: {result.get('count', 0)}件\n\n"
    
    for i, item in enumerate(result.get("results", []), 1):
        output += f"{i}. {item.get('title', '')}\n"
        output += f"   URL: {item.get('url', '')}\n"
        if item.get('content'):
            content = item.get('content', '')[:200]
            output += f"   概要: {content}...\n"
        output += "\n"
    
    return output

















