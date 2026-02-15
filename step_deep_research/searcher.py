#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索エージェント（Searcher）
"""

import os
import httpx
from typing import Dict, Any, List
from datetime import datetime

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import SearchResult, TaskTool
from .source_quality_filter import SourceQualityFilter

try:
    from manaos_integrations._paths import RAG_MEMORY_PORT, SEARXNG_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import RAG_MEMORY_PORT, SEARXNG_PORT  # type: ignore
    except Exception:  # pragma: no cover
        SEARXNG_PORT = int(os.getenv("SEARXNG_PORT", "8080"))
        RAG_MEMORY_PORT = int(os.getenv("RAG_MEMORY_PORT", "5103"))

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchSearcher")


class Searcher:
    """検索エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Searcher設定
        """
        self.config = config
        self.sources = config.get("sources", ["web", "rag"])
        self.max_results_per_query = config.get("max_results_per_query", 10)
        self.searxng_url = config.get(
            "searxng_url",
            os.getenv("SEARXNG_URL", f"http://127.0.0.1:{SEARXNG_PORT}"),
        )
        self.rag_api_url = config.get(
            "rag_api_url",
            os.getenv("RAG_MEMORY_URL", f"http://127.0.0.1:{RAG_MEMORY_PORT}"),
        )
        
        # ソース品質フィルタ初期化
        self.quality_filter = SourceQualityFilter()
    
    def search(self, query: str, tool: TaskTool, max_results: int = None) -> List[SearchResult]:
        """
        検索実行
        
        Args:
            query: 検索クエリ
            tool: 検索ツール
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        if max_results is None:
            max_results = self.max_results_per_query
        
        try:
            if tool == TaskTool.SEARCH:
                return self._web_search(query, max_results)
            elif tool == TaskTool.RAG:
                return self._rag_search(query, max_results)
            elif tool == TaskTool.DOCS:
                return self._docs_search(query, max_results)
            elif tool == TaskTool.PDF:
                return self._pdf_search(query, max_results)
            else:
                logger.info(f"No search needed for tool: {tool}")
                return []
        except Exception as e:
            error_handler.handle_error(
                e,
                f"Search failed for query: {query}",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM
            )
            return []
    
    def _web_search(self, query: str, max_results: int) -> List[SearchResult]:
        """
        Web検索（SearXNG使用）
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.searxng_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "engines": "google,bing,duckduckgo"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", [])[:max_results]:
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="web",
                        timestamp=datetime.now()
                    )
                    results.append(result)
                
                logger.info(f"Web search: {len(results)} results for '{query}'")
                
                # ソース品質フィルタ適用
                filtered_results = self.quality_filter.filter_and_rank_sources(results)
                
                return filtered_results
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []
    
    def _rag_search(self, query: str, max_results: int) -> List[SearchResult]:
        """
        RAG検索
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.rag_api_url}/search",
                    json={
                        "query": query,
                        "top_k": max_results
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", [])[:max_results]:
                    result = SearchResult(
                        title=item.get("title", query),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="rag",
                        timestamp=datetime.now()
                    )
                    results.append(result)
                
                logger.info(f"RAG search: {len(results)} results for '{query}'")
                
                # ソース品質フィルタ適用
                filtered_results = self.quality_filter.filter_and_rank_sources(results)
                
                return filtered_results
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")
            return []
    
    def _docs_search(self, query: str, max_results: int) -> List[SearchResult]:
        """
        ドキュメント検索
        Obsidian統合を使用してMarkdownドキュメントを検索
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        try:
            from obsidian_integration import ObsidianIntegration
            from pathlib import Path
            
            # Obsidian Vaultパスを取得（環境変数から）
            import os
            vault_path = os.getenv(
                "OBSIDIAN_VAULT_PATH",
                os.path.expanduser("~/Documents/Obsidian Vault")
            )
            
            # Obsidian統合を初期化
            obsidian = ObsidianIntegration(vault_path)
            
            if not obsidian.is_available():
                logger.warning(f"Obsidian Vaultが見つかりません: {vault_path}")
                return []
            
            # ノートを検索
            note_paths = obsidian.search_notes(query)
            
            results = []
            for note_path in note_paths[:max_results]:
                try:
                    # ノートの内容を読み込む
                    note_name = note_path.name if isinstance(note_path, Path) else str(note_path)
                    content = obsidian.read_note(note_name)
                    
                    if content:
                        # 検索クエリを含む部分を抽出（簡易版：最初の200文字）
                        query_lower = query.lower()
                        content_lower = content.lower()
                        
                        if query_lower in content_lower:
                            # クエリの位置を探す
                            index = content_lower.find(query_lower)
                            start = max(0, index - 100)
                            end = min(len(content), index + len(query) + 100)
                            snippet = content[start:end].strip()
                        else:
                            # クエリが見つからない場合は最初の200文字
                            snippet = content[:200].strip()
                        
                        result = SearchResult(
                            title=note_name.replace(".md", ""),
                            url=f"obsidian://open?vault={Path(vault_path).name}&file={note_name}",
                            snippet=snippet,
                            source="docs",
                            timestamp=datetime.now()
                        )
                        results.append(result)
                
                except Exception as e:
                    logger.warning(f"ノート処理エラー ({note_path}): {e}")
                    continue
            
            logger.info(f"Docs search: {len(results)} results for '{query}'")
            
            # ソース品質フィルタ適用
            filtered_results = self.quality_filter.filter_and_rank_sources(results)
            
            return filtered_results
            
        except ImportError:
            logger.warning("Obsidian統合が利用できません。ドキュメント検索をスキップします。")
            return []
        except Exception as e:
            logger.warning(f"Docs search failed: {e}")
            return []
    
    def _pdf_search(self, query: str, max_results: int) -> List[SearchResult]:
        """
        PDF検索
        ローカルディレクトリからPDFファイルを検索
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        try:
            from pathlib import Path
            import os
            
            # PDF検索ディレクトリを取得（環境変数から）
            pdf_dirs = os.getenv(
                "PDF_SEARCH_DIRS",
                os.path.expanduser("~/Documents")
            ).split(os.pathsep)
            
            results = []
            query_lower = query.lower()
            
            # PDFファイルを検索
            for pdf_dir in pdf_dirs:
                pdf_path = Path(pdf_dir)
                if not pdf_path.exists():
                    continue
                
                # PDFファイルを検索
                for pdf_file in pdf_path.rglob("*.pdf"):
                    try:
                        # ファイル名で検索（簡易版）
                        file_name_lower = pdf_file.stem.lower()
                        
                        if query_lower in file_name_lower:
                            # PDFの内容は読み込まない（重い処理のため）
                            # 実際の実装では、PyPDF2やpdfplumberを使用してテキスト抽出
                            result = SearchResult(
                                title=pdf_file.stem,
                                url=str(pdf_file.absolute()),
                                snippet=f"PDFファイル: {pdf_file.name}",
                                source="pdf",
                                timestamp=datetime.fromtimestamp(pdf_file.stat().st_mtime)
                            )
                            results.append(result)
                            
                            if len(results) >= max_results:
                                break
                    
                    except Exception as e:
                        logger.warning(f"PDFファイル処理エラー ({pdf_file}): {e}")
                        continue
                    
                    if len(results) >= max_results:
                        break
                
                if len(results) >= max_results:
                    break
            
            logger.info(f"PDF search: {len(results)} results for '{query}'")
            
            # ソース品質フィルタ適用
            filtered_results = self.quality_filter.filter_and_rank_sources(results)
            
            return filtered_results
            
        except Exception as e:
            logger.warning(f"PDF search failed: {e}")
            return []


