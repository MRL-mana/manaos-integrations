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

# ── EpisodicMemory 直接接続 ────────────────────────
_episodic_memory = None
_episodic_lock = threading.Lock()

# ── LessonsRecorder 直接接続 ──────────────────────
_lessons_recorder = None
_lessons_lock = threading.Lock()

# ── AgentTracker 直接接続 ──────────────────────────
_agent_tracker = None
_agent_tracker_lock = threading.Lock()


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


def _get_episodic():
    """シングルトンで EpisodicMemory を返す（遅延初期化）"""
    global _episodic_memory
    if _episodic_memory is None:
        with _episodic_lock:
            if _episodic_memory is None:
                try:
                    from episodic_memory import EpisodicMemory
                    _episodic_memory = EpisodicMemory()
                    logger.info("EpisodicMemory 初期化成功")
                except Exception as e:
                    logger.error(f"EpisodicMemory 初期化失敗: {e}")
                    _episodic_memory = None
    return _episodic_memory


def _get_lessons():
    """シングルトンで LessonsRecorder を返す（遅延初期化）"""
    global _lessons_recorder
    if _lessons_recorder is None:
        with _lessons_lock:
            if _lessons_recorder is None:
                try:
                    from lessons_recorder import LessonsRecorder
                    _lessons_recorder = LessonsRecorder()
                    logger.info("LessonsRecorder 初期化成功")
                except Exception as e:
                    logger.error(f"LessonsRecorder 初期化失敗: {e}")
                    _lessons_recorder = None
    return _lessons_recorder


def _get_tracker():
    """シングルトンで AgentTracker を返す（遅延初期化）"""
    global _agent_tracker
    if _agent_tracker is None:
        with _agent_tracker_lock:
            if _agent_tracker is None:
                try:
                    from agent_tracker import AgentTracker
                    _agent_tracker = AgentTracker()
                    logger.info("AgentTracker 初期化成功")
                except Exception as e:
                    logger.error(f"AgentTracker 初期化失敗: {e}")
                    _agent_tracker = None
    return _agent_tracker


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


def _store_to_episodic(text: str, session_id: str, source: str = "mcp-chat") -> Optional[dict]:
    """EpisodicMemory に会話履歴を保存（fire-and-forget 用）"""
    em = _get_episodic()
    if em is None:
        return None
    try:
        entry = em.store(
            content=text,
            session_id=session_id,
            memory_type="conversation",
            importance_score=0.7,  # MCP経由の記録は重要度高め
            tags=[source, "mcp"],
        )
        return {"entry_id": entry.entry_id, "expires_at": entry.expires_at}
    except Exception as e:
        logger.warning(f"EpisodicMemory store エラー: {e}")
        return None


def _store_to_rag(text: str, source: str = "mcp-chat", session_id: Optional[str] = None) -> dict:
    """RAGv2 + EpisodicMemory にデュアル書き込み、並行して Flask API にも記録"""
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

    # EpisodicMemory にも並行記録（fire-and-forget）
    _sid = session_id or f"mcp-{source}"
    threading.Thread(
        target=_store_to_episodic,
        args=(text, _sid, source),
        daemon=True,
    ).start()

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


def _record_lesson(
    instruction: str,
    category: str = "other",
    trigger_text: str = "",
    session_id: str = "",
) -> dict:
    """指摘・訂正を教訓として記録する"""
    lr = _get_lessons()
    if lr is None:
        return {"error": "LessonsRecorder が利用不可"}
    try:
        lesson = lr.record_lesson(
            instruction=instruction,
            category=category,
            trigger_text=trigger_text,
            session_id=session_id,
        )
        return {
            "status": "recorded",
            "lesson_id": lesson.lesson_id,
            "instruction": lesson.instruction,
            "category": lesson.category,
            "access_count": lesson.access_count,
        }
    except Exception as e:
        return {"error": str(e)}


def _search_lessons(query: str = "", category: Optional[str] = None, limit: int = 10) -> dict:
    """過去の教訓・失敗パターンを検索する"""
    lr = _get_lessons()
    if lr is None:
        return {"error": "LessonsRecorder が利用不可"}
    try:
        lessons = lr.search_lessons(query=query, category=category, limit=limit)
        context = lr.get_context_text(limit=limit, category=category)
        return {
            "query": query,
            "count": len(lessons),
            "context": context,
            "lessons": [
                {
                    "lesson_id": l.lesson_id,
                    "instruction": l.instruction,
                    "category": l.category,
                    "access_count": l.access_count,
                    "created_at": l.created_at,
                }
                for l in lessons
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _track_agent(agent_name: str, task_summary: str = "", session_id: str = "") -> dict:
    """エージェント使用をトラッキングする"""
    tracker = _get_tracker()
    if tracker is None:
        return {"error": "AgentTracker が利用不可"}
    try:
        record = tracker.track(
            agent_name=agent_name,
            task_summary=task_summary,
            session_id=session_id,
        )
        stats = tracker.get_stats(agent_name)
        return {
            "status": "tracked",
            "agent_name": agent_name,
            "rank": stats.rank,
            "total_uses": stats.total_uses,
            "recorded_at": record.recorded_at,
        }
    except Exception as e:
        return {"error": str(e)}


def _audit_agents(agents_dir: Optional[str] = None) -> dict:
    """エージェント品質スコアを確認する"""
    tracker = _get_tracker()
    if tracker is None:
        return {"error": "AgentTracker が利用不可"}
    try:
        result = tracker.audit_agents_dir(agents_dir=agents_dir)
        return result
    except Exception as e:
        return {"error": str(e)}


def _metrics_rag() -> dict:
    """RAGv2 + EpisodicMemory の統計情報"""
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
        rag_metrics = {
            "rag_v2_available": True,
            "total_entries": total,
            "avg_importance": avg_imp,
            "max_importance": max_imp,
            "db_path": str(rag.db_path),
            "backend": "rag_memory_v2",
        }
    except Exception as e:
        rag_metrics = {"error": str(e), "rag_v2_available": True}

    # EpisodicMemory 統計
    em = _get_episodic()
    if em is None:
        episodic_metrics = {"episodic_available": False}
    else:
        try:
            stats = em.stats()
            episodic_metrics = {"episodic_available": True, **stats}
        except Exception as e:
            episodic_metrics = {"episodic_available": True, "error": str(e)}

    return {**rag_metrics, "episodic": episodic_metrics}


# ── ヘルスチェック HTTP (mcp_common 使用) ───────────


# ── MCP サーバー ────────────────────────────────────
if MCP_AVAILABLE:
    server = Server("mrl-memory")  # type: ignore[possibly-unbound]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
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
            Tool(  # type: ignore[possibly-unbound]
                name="memory_store",
                description="テキストをManaOSメモリに保存。重要な決定・学び・コンテキスト・アクション履歴を RAGv2 + 中期記憶(EpisodicMemory) にデュアル記録。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "保存するテキスト"},
                        "source": {"type": "string", "description": "情報源", "default": "mcp-chat"},
                        "session_id": {"type": "string", "description": "セッションID（エピソード記憶グループ化用）"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
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
            Tool(  # type: ignore[possibly-unbound]
                name="memory_metrics",
                description="MRL Memory (RAGv2) のメトリクス・統計情報を取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="lessons_record",
                description="指摘・訂正・失敗パターンを教訓として永続記録する。セッション開始時に自動注入して同じミスを繰り返さない。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "教訓テキスト（例: コードブロックを省略しない）"},
                        "category": {
                            "type": "string",
                            "description": "カテゴリ: output_format / behavior / technical / context / other",
                            "default": "other",
                        },
                        "trigger_text": {"type": "string", "description": "指摘を引き起こした元テキスト（任意）", "default": ""},
                        "session_id": {"type": "string", "description": "セッションID（任意）", "default": ""},
                    },
                    "required": ["instruction"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="lessons_search",
                description="過去の教訓・失敗パターンを検索してセッション注入テキストを生成する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（空文字で全件取得）", "default": ""},
                        "category": {"type": "string", "description": "カテゴリでフィルタ（任意）"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="agent_track",
                description="Claudeエージェントの使用をトラッキングしランク（N/N-C/N-B/N-A/N-S）を更新する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "description": "エージェント名"},
                        "task_summary": {"type": "string", "description": "タスク概要（任意）", "default": ""},
                        "session_id": {"type": "string", "description": "セッションID（任意）", "default": ""},
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="agent_audit",
                description="エージェント定義ファイル（.md）を品質スコアリング（100点満点）してフィードバックを返す。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agents_dir": {"type": "string", "description": "エージェントディレクトリパス（省略で~/.claude/agents）"},
                    },
                },
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
                    None, lambda: _store_to_rag(
                        arguments["text"],
                        arguments.get("source", "mcp-chat"),
                        arguments.get("session_id"),
                    )
                )
            elif name == "memory_context":
                result = await loop.run_in_executor(
                    None, lambda: _context_rag(arguments["query"], arguments.get("limit", 5))
                )
            elif name == "memory_metrics":
                result = await loop.run_in_executor(None, _metrics_rag)
            elif name == "lessons_record":
                result = await loop.run_in_executor(
                    None, lambda: _record_lesson(
                        arguments["instruction"],
                        arguments.get("category", "other"),
                        arguments.get("trigger_text", ""),
                        arguments.get("session_id", ""),
                    )
                )
            elif name == "lessons_search":
                result = await loop.run_in_executor(
                    None, lambda: _search_lessons(
                        arguments.get("query", ""),
                        arguments.get("category"),
                        arguments.get("limit", 10),
                    )
                )
            elif name == "agent_track":
                result = await loop.run_in_executor(
                    None, lambda: _track_agent(
                        arguments["agent_name"],
                        arguments.get("task_summary", ""),
                        arguments.get("session_id", ""),
                    )
                )
            elif name == "agent_audit":
                result = await loop.run_in_executor(
                    None, lambda: _audit_agents(arguments.get("agents_dir"))
                )
            else:
                result = {"error": f"不明なツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]  # type: ignore[possibly-unbound]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]  # type: ignore[possibly-unbound]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # ヘルスチェック
    start_health_thread("mrl-memory-mcp", HEALTH_PORT)

    async with stdio_server() as (read_stream, write_stream):  # type: ignore[possibly-unbound]
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
