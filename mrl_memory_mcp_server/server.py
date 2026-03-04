"""
MRL Memory MCPサーバー (RAGMemoryEnhancedV2 直接接続版)
========================================================
エージェントの会話・アクション履歴を RAGMemoryEnhancedV2 に直接保存・検索する。
Flask HTTP API (port 5105) は補助的フォールバックとして併用。

ツール一覧:
  - memory_search : セマンティック検索（RAGv2 + テキスト検索フォールバック）
  - memory_store  : 会話・決定・アクション履歴を記憶に保存
  - memory_context: LLMコンテキスト用メモリ取得（検索 + 整形テキスト）
  - memory_metrics: メモリDB統計・設定情報を取得
"""

import os
import sys
import json
import asyncio
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Optional

# 親ディレクトリ + scripts/misc をパスに追加
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts" / "misc"))

from mcp_common import check_mcp_available, start_health_thread, get_mcp_logger

try:
    from manaos_integrations._paths import MRL_MEMORY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MRL_MEMORY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MRL_MEMORY_PORT = int(os.getenv("MRL_MEMORY_PORT", "5105"))

MCP_AVAILABLE = check_mcp_available()
if MCP_AVAILABLE:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

try:
    import requests as _requests
except ImportError:
    _requests = None

logger = get_mcp_logger(__name__)
if not MCP_AVAILABLE:
    logger.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("MRL_MEMORY_API_URL", f"http://127.0.0.1:{MRL_MEMORY_PORT}")
API_KEY = os.getenv("MRL_MEMORY_API_KEY", os.getenv("API_KEY", ""))
HEALTH_PORT = int(os.getenv("MRL_MEMORY_MCP_HEALTH_PORT", "5113"))
HTTP_TIMEOUT = 5  # Flask API フォールバック用（短め）

# ── RAGMemoryEnhancedV2 直接接続 ──────────────────
_rag_memory = None
_rag_lock = threading.Lock()


def _get_rag():
    """シングルトンで RAGMemoryEnhancedV2 を返す（遅延初期化）"""
    global _rag_memory
    if _rag_memory is None:
        with _rag_lock:
            if _rag_memory is None:
                try:
                    from rag_memory_enhanced_v2 import RAGMemoryEnhancedV2
                    _rag_memory = RAGMemoryEnhancedV2()
                    logger.info("RAGMemoryEnhancedV2 初期化成功")
                except Exception as e:
                    logger.error(f"RAGMemoryEnhancedV2 初期化失敗: {e}")
                    _rag_memory = None
    return _rag_memory


# ── Flask API フォールバック（fire-and-forget）─────
def _flask_headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _flask_post_async(path: str, body: dict):
    """Flask APIにバックグラウンドで記録（失敗しても無視）"""
    if _requests is None:
        return
    try:
        _requests.post(
            f"{API_BASE}{path}", json=body,
            headers=_flask_headers(), timeout=HTTP_TIMEOUT
        )
    except Exception:
        pass


def _store_to_rag(text: str, source: str = "mcp-chat") -> dict:
    """RAGv2 に記憶を保存し、並行して Flask API にも記録"""
    rag = _get_rag()
    if rag is None:
        # v2 が使えない場合は Flask API に転送
        if _requests is None:
            return {"error": "RAGMemoryEnhancedV2 も requests も利用不可"}
        try:
            r = _requests.post(
                f"{API_BASE}/api/memory/process",
                json={"text": text, "source": source, "enable_rehearsal": True},
                headers=_flask_headers(), timeout=HTTP_TIMEOUT
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # v2 に保存（会話・アクション履歴は必ず保存するため force_importance=1.0）
    try:
        entry = rag.add_memory(
            content=text,
            metadata={"source": source, "origin": "mcp-chat"},
            force_importance=1.0,
        )
        entry_dict = asdict(entry) if entry is not None else None
        # エンベディング（大きいデータ）はレスポンスから除外
        if entry_dict and "embedding" in entry_dict:
            del entry_dict["embedding"]

        result = {
            "status": "stored",
            "entry": entry_dict,
            "backend": "rag_memory_v2",
        }
    except Exception as e:
        logger.warning(f"RAGv2 add_memory エラー: {e}")
        result = {"error": str(e)}

    # Flask APIにも並行記録（fire-and-forget）
    threading.Thread(
        target=_flask_post_async,
        args=("/api/memory/process", {"text": text, "source": source, "enable_rehearsal": True}),
        daemon=True,
    ).start()

    return result


def _search_rag(query: str, limit: int = 10) -> dict:
    """RAGv2 でセマンティック検索"""
    rag = _get_rag()
    if rag is None:
        if _requests is None:
            return {"error": "RAGMemoryEnhancedV2 も requests も利用不可"}
        try:
            r = _requests.post(
                f"{API_BASE}/api/memory/search",
                json={"query": query, "limit": limit},
                headers=_flask_headers(), timeout=HTTP_TIMEOUT
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    try:
        hits = rag.semantic_search(query, limit=limit)
        results = []
        for entry, score in hits:
            d = asdict(entry)
            d.pop("embedding", None)  # 大きいデータを除外
            results.append({"entry": d, "score": round(score, 4)})
        return {"query": query, "results": results, "count": len(results), "backend": "rag_memory_v2"}
    except Exception as e:
        logger.warning(f"RAGv2 semantic_search エラー: {e}")
        return {"error": str(e)}


def _context_rag(query: str, limit: int = 5) -> dict:
    """RAGv2 でコンテキスト取得（整形テキスト付き）"""
    search_result = _search_rag(query, limit=limit)
    if "error" in search_result:
        return search_result

    results = search_result.get("results", [])
    lines = []
    for i, r in enumerate(results, 1):
        entry = r.get("entry", {})
        score = r.get("score", 0)
        content = entry.get("content", "")
        created = entry.get("created_at", "")[:10]
        lines.append(f"[{i}] (類似度:{score:.2f}, {created}) {content}")

    context_text = "\n".join(lines) if lines else "関連する記憶が見つかりませんでした。"
    return {
        "query": query,
        "context": context_text,
        "length": len(context_text),
        "count": len(results),
        "backend": "rag_memory_v2",
    }


def _metrics_rag() -> dict:
    """RAGv2 の統計情報"""
    rag = _get_rag()
    if rag is None:
        return {"error": "RAGMemoryEnhancedV2 が利用不可", "rag_v2_available": False}
    try:
        from contextlib import contextmanager
        with rag.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(importance_score), MAX(importance_score) FROM memory_entries")
            row = cursor.fetchone()
            avg_imp = round(row[0] or 0, 3)
            max_imp = round(row[1] or 0, 3)
        return {
            "rag_v2_available": True,
            "total_entries": total,
            "avg_importance": avg_imp,
            "max_importance": max_imp,
            "db_path": str(rag.db_path),
            "backend": "rag_memory_v2",
        }
    except Exception as e:
        return {"error": str(e), "rag_v2_available": True}


# ── ヘルスチェック HTTP (mcp_common 使用) ───────────


# ── MCP サーバー ────────────────────────────────────
if MCP_AVAILABLE:
    server = Server("mrl-memory")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="memory_search",
                description="ManaOSメモリを検索。過去の会話・決定事項・技術メモなどを取得。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memory_store",
                description="テキストをManaOSメモリに保存。重要な決定・学び・コンテキスト・アクション履歴を記憶。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "保存するテキスト"},
                        "source": {"type": "string", "description": "情報源", "default": "mcp-chat"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="memory_context",
                description="LLMコンテキスト用にメモリを取得。関連する過去の記憶を文脈として返す。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "コンテキストクエリ"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memory_metrics",
                description="MRL Memory (RAGv2) のメトリクス・統計情報を取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            loop = asyncio.get_event_loop()
            if name == "memory_search":
                result = await loop.run_in_executor(
                    None, lambda: _search_rag(arguments["query"], arguments.get("limit", 10))
                )
            elif name == "memory_store":
                result = await loop.run_in_executor(
                    None, lambda: _store_to_rag(arguments["text"], arguments.get("source", "mcp-chat"))
                )
            elif name == "memory_context":
                result = await loop.run_in_executor(
                    None, lambda: _context_rag(arguments["query"], arguments.get("limit", 5))
                )
            elif name == "memory_metrics":
                result = await loop.run_in_executor(None, _metrics_rag)
            else:
                result = {"error": f"不明なツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # ヘルスチェック
    start_health_thread("mrl-memory-mcp", HEALTH_PORT)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
