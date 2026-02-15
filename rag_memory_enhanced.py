#!/usr/bin/env python3
"""
🧠 RAG記憶進化システム（互換性レイヤー）

⚠️ このファイルは後方互換性のためのラッパーです。
   実装は rag_memory_enhanced_v2.py に統合されました。
   新規コードでは RAGMemoryEnhancedV2 を直接使用してください。

旧実装のバックアップ: rag_memory_enhanced_v1_backup.py
"""

from rag_memory_enhanced_v2 import RAGMemoryEnhancedV2, MemoryEntry  # noqa: F401
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os

try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RAGMemoryEnhanced(RAGMemoryEnhancedV2):
    """
    RAG記憶進化システム（V2への互換ブリッジ）

    旧インターフェースを維持しつつ、内部実装はV2（セマンティック検索対応）を使用。
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        model: str = "qwen2.5:14b",
        config_path: Optional[Path] = None,
        **kwargs
    ):
        # config_pathから設定を読み込んで反映
        if config_path and config_path.exists():
            import json
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                ollama_url = config.get("ollama_url", ollama_url)
                model = config.get("model", model)
            except Exception:
                pass

        # V1はrag_memory.dbを使っていたので互換維持
        if db_path is None:
            db_path = Path(__file__).parent / "rag_memory.db"

        super().__init__(
            db_path=db_path,
            ollama_url=ollama_url,
            model=model,
            **kwargs
        )
        logger.info("RAGMemoryEnhanced → V2互換ブリッジで起動")

    def search(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """V1互換: searchメソッド（V2のsemantic_searchをラップ）"""
        results = self.semantic_search(query, limit, min_importance)
        return [entry for entry, _score in results]


# 後方互換性のため
__all__ = ["RAGMemoryEnhanced", "MemoryEntry"]

