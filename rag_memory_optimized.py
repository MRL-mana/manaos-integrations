#!/usr/bin/env python3
"""
🧠 RAG記憶進化システム（最適化版 - 互換性レイヤー）

⚠️ このファイルは後方互換性のためのラッパーです。
   実装は rag_memory_enhanced_v2.py に統合されました。
   新規コードでは RAGMemoryEnhancedV2 を直接使用してください。

旧実装のバックアップ: rag_memory_optimized_backup.py
"""

from rag_memory_enhanced_v2 import RAGMemoryEnhancedV2, MemoryEntry  # noqa: F401
from typing import Dict, Any, Optional, List
from pathlib import Path

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RAGMemoryOptimized(RAGMemoryEnhancedV2):
    """
    RAG記憶進化システム（最適化版 → V2互換ブリッジ）

    V2は元々DB接続プール＋キャッシュシステムを使用しており、
    旧 Optimized 版の機能をすべて包含しています。
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        **kwargs
    ):
        if db_path is None:
            db_path = Path(__file__).parent / "rag_memory.db"

        super().__init__(
            db_path=db_path,
            ollama_url=ollama_url,
            model=model,
            **kwargs
        )
        logger.info("RAGMemoryOptimized → V2互換ブリッジで起動")

    def search(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """V1互換: searchメソッド"""
        results = self.semantic_search(query, limit, min_importance)
        return [entry for entry, _score in results]


# 後方互換性のため
__all__ = ["RAGMemoryOptimized", "MemoryEntry"]
