#!/usr/bin/env python3
"""
記憶システム統合ブリッジ
UnifiedMemory + Mem0 + Phase2 を一本化し、「会話→記憶→検索→コンテキスト注入」の一貫フローを提供
"""

import os
from typing import Dict, Any, List, Optional

# ロガー
try:
    from manaos_logger import get_logger, get_service_logger
except ImportError:
    import logging
    def get_logger(n): return logging.getLogger(n)
logger = get_service_logger("memory-integration-bridge")

# UnifiedMemory
MEMORY_UNIFIED = None
MEMORY_UNIFIED_AVAILABLE = False
try:
    from memory_unified import UnifiedMemory
    MEMORY_UNIFIED = UnifiedMemory()
    MEMORY_UNIFIED_AVAILABLE = True
except Exception as e:
    logger.warning(f"UnifiedMemory 初期化スキップ: {e}")

# Mem0（統合APIから渡される場合は使用）
MEM0_AVAILABLE = False

# Phase2 メモ
PHASE2_AVAILABLE = False
try:
    from phase2_reflection_memo import get_memo_context_for_messages, get_memos_for_theme, theme_id_from_first_user_content
    PHASE2_AVAILABLE = True
except ImportError:
    get_memo_context_for_messages = None
    get_memos_for_theme = None
    theme_id_from_first_user_content = None


def memory_store(
    content: Dict[str, Any],
    format_type: str = "auto",
    memory_unified=None,
    mem0_integration=None
) -> str:
    """
    記憶への保存（統一入口）
    UnifiedMemory を優先、Mem0 にもフォワード（利用可能時）
    memory_unified: 統合APIの integrations.get("memory_unified") を渡すと使用。未指定時は自前の MEMORY_UNIFIED
    mem0_integration: 統合APIの integrations.get("mem0") を渡すと Mem0 にもフォワード
    """
    memory_id = ""
    um = memory_unified or (MEMORY_UNIFIED if MEMORY_UNIFIED_AVAILABLE else None)
    if um:
        try:
            memory_id = um.store(content, format_type)
        except Exception as e:
            logger.warning(f"UnifiedMemory store エラー: {e}")
            raise

    # Mem0 にもフォワード（AIエージェント向け）
    if mem0_integration and hasattr(mem0_integration, "is_available") and mem0_integration.is_available():
        try:
            text = content.get("content", str(content))
            metadata = content.get("metadata", {})
            user_id = metadata.get("user_id", "default")
            mem0_integration.add_memory(text, user_id, metadata)
        except Exception as e:
            logger.debug(f"Mem0 フォワード スキップ: {e}")

    return memory_id or "local_only"


def memory_recall(
    query: str,
    scope: str = "all",
    limit: int = 10,
    include_phase2: bool = True,
    memory_unified=None
) -> List[Dict[str, Any]]:
    """
    記憶からの検索（統一出口）
    UnifiedMemory の結果に Phase2 メモを統合（同一テーマの振り返り）
    memory_unified: 統合APIの integrations.get("memory_unified") を渡すと使用
    """
    results = []
    um = memory_unified or (MEMORY_UNIFIED if MEMORY_UNIFIED_AVAILABLE else None)
    if um:
        try:
            results = um.recall(query, scope, limit)
        except Exception as e:
            logger.warning(f"UnifiedMemory recall エラー: {e}")

    # Phase2: クエリからテーマIDを推定し、同一テーマの振り返りメモを追加
    if include_phase2 and PHASE2_AVAILABLE and theme_id_from_first_user_content:
        try:
            theme_id = theme_id_from_first_user_content(query[:500])
            if theme_id:
                phase2_memos = get_memos_for_theme(theme_id)[:3]
                for m in phase2_memos:
                    results.append({
                        "id": m.get("thread_id", "") + "_phase2",
                        "type": "phase2_reflection",
                        "timestamp": m.get("ts", ""),
                        "content": f"満足度{m.get('satisfaction', '?')}: {m.get('reason', '')[:120]}",
                        "metadata": {"theme_id": theme_id, "source": "phase2"}
                    })
        except Exception as e:
            logger.debug(f"Phase2 メモ統合スキップ: {e}")

    return results[:limit]


def get_memo_context_for_chat(messages: List[Dict[str, Any]], max_memos: int = 5) -> str:
    """
    会話メッセージから同一テーマの振り返りメモを取得し、注入用テキストを返す
    コンパニオン・LLM チャットで使用
    """
    if not PHASE2_AVAILABLE or not get_memo_context_for_messages:
        return ""
    try:
        return get_memo_context_for_messages(messages, max_memos=max_memos)
    except Exception as e:
        logger.debug(f"Phase2 メモコンテキスト取得エラー: {e}")
        return ""
