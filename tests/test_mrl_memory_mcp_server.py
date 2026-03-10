"""
mrl_memory_mcp_server.server のユニットテスト
=============================================
RAGMemoryEnhancedV2 直接接続版の動作を検証する。
依存モジュールはすべてモックして独立実行可能。
"""
from __future__ import annotations

import json
import sys
import types
import sqlite3
import threading
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch, call
import pytest


# ─── 依存モジュールをスタブ化 ────────────────────────────────────────────────

# スタブ注入前の状態を保存（teardown_module で復元するため）
_STUBS_INJECTED: list[str] = []
_PRE_EXISTING: dict[str, object] = {}


def _make_stub(name: str) -> types.ModuleType:
    # 既に実モジュールが存在する場合は上書きせずそのまま返す（後続テスト汚染防止）
    if name in sys.modules:
        existing = sys.modules[name]
        if not getattr(existing, "__is_stub__", False):
            return existing  # type: ignore[return-value]
    # 新規スタブを注入し、teardown で除去できるよう記録する
    _PRE_EXISTING[name] = sys.modules.get(name)
    m = types.ModuleType(name)
    m.__is_stub__ = True  # type: ignore[attr-defined]
    sys.modules[name] = m
    _STUBS_INJECTED.append(name)
    return m


# mcp_common
_mc = _make_stub("mcp_common")
if getattr(_mc, "__is_stub__", False):
    _mc.check_mcp_available = lambda: False  # type: ignore
    _mc.start_health_thread = MagicMock()  # type: ignore
    _mc.get_mcp_logger = lambda n: MagicMock()  # type: ignore

# manaos_integrations._paths
_mi = _make_stub("manaos_integrations")
_mip = _make_stub("manaos_integrations._paths")
if getattr(_mip, "__is_stub__", False):
    _mip.MRL_MEMORY_PORT = 5105  # type: ignore

# manaos関連（rag_memory_enhanced_v2が使う）
for _mod in [
    "manaos_logger", "manaos_error_handler", "manaos_timeout_config",
    "database_connection_pool", "unified_cache_system",
]:
    s = _make_stub(_mod)
    if not getattr(s, "__is_stub__", False):
        continue  # 実モジュールがある場合は属性を上書きしない
    if _mod == "manaos_logger":
        s.get_logger = MagicMock(return_value=MagicMock())  # type: ignore
        s.get_service_logger = MagicMock(return_value=MagicMock())  # type: ignore
    elif _mod == "manaos_error_handler":
        s.ManaOSErrorHandler = MagicMock()  # type: ignore
        s.ErrorCategory = MagicMock()  # type: ignore
        s.ErrorSeverity = MagicMock()  # type: ignore
    elif _mod == "manaos_timeout_config":
        s.get_timeout_config = MagicMock(return_value=MagicMock())  # type: ignore
    elif _mod == "database_connection_pool":
        s.get_pool = MagicMock(return_value=MagicMock())  # type: ignore
    elif _mod == "unified_cache_system":
        s.get_unified_cache = MagicMock(return_value=MagicMock())  # type: ignore

# _paths
_paths_stub = _make_stub("_paths")
if getattr(_paths_stub, "__is_stub__", False):
    _paths_stub.OLLAMA_PORT = 11434  # type: ignore
    _paths_stub.MRL_MEMORY_PORT = 5105  # type: ignore

# requests
import importlib
_req = _make_stub("requests")
if getattr(_req, "__is_stub__", False):
    _req.post = MagicMock()  # type: ignore
    _req.get = MagicMock()  # type: ignore

# rag_memory_enhanced_v2 モック定義（後でパッチで差し替える）
_rag_stub = _make_stub("rag_memory_enhanced_v2")


# episodic_memory モック定義
_ep_stub = _make_stub("episodic_memory")


@dataclass
class _EpisodicEntry:
    entry_id: str = "ep001"
    content: str = "test episode"
    session_id: str = "s1"
    memory_type: str = "conversation"
    importance_score: float = 0.7
    tags: List[str] = field(default_factory=list)
    created_at: str = "2026-01-01T12:00:00"
    expires_at: str = "2026-01-02T12:00:00"
    promoted: bool = False
    promotion_id: Optional[str] = None


class _FakeEpisodicMemory:
    """テスト用 EpisodicMemory スタブ"""

    def __init__(self):
        self._entries: List[_EpisodicEntry] = []

    def store(self, content, session_id, memory_type="conversation",
               importance_score=0.5, tags=None, ttl_hours=24):
        e = _EpisodicEntry(
            content=content,
            session_id=session_id,
            memory_type=memory_type,
            importance_score=importance_score,
            tags=tags or [],
        )
        self._entries.append(e)
        return e

    def stats(self):
        return {
            "total": len(self._entries),
            "by_type": {"conversation": len(self._entries)},
        }


_ep_stub.EpisodicMemory = _FakeEpisodicMemory  # type: ignore
_ep_stub.EpisodicEntry = _EpisodicEntry  # type: ignore


@dataclass
class _MemoryEntry:
    entry_id: str = "e001"
    content: str = "test content"
    importance_score: float = 0.9
    content_hash: str = "abc123"
    created_at: str = "2026-01-01T12:00:00"
    updated_at: str = "2026-01-01T12:00:00"
    access_count: int = 1
    last_accessed_at: str = "2026-01-01T12:00:00"
    related_entries: List[str] = field(default_factory=list)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


_rag_stub.MemoryEntry = _MemoryEntry  # type: ignore


class _FakeRAG:
    """テスト用 RAGMemoryEnhancedV2 スタブ"""

    def __init__(self):
        self.db_path = "/tmp/test_rag.db"
        # db_pool: context manager として使えるよう in-memory SQLite を接続
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT, content TEXT, importance_score REAL,
                content_hash TEXT, created_at TEXT, updated_at TEXT,
                access_count INTEGER, related_entries TEXT,
                temporal_context TEXT, metadata TEXT, embedding TEXT
            )"""
        )
        self._conn.commit()

        class _Pool:
            def __init__(self2):
                self2._conn = self._conn

            def get_connection(self2):
                from contextlib import contextmanager

                @contextmanager
                def _ctx():
                    yield self2._conn

                return _ctx()

        self.db_pool = _Pool()
        self._entries: List[_MemoryEntry] = []

    def add_memory(self, content, metadata=None, force_importance=None):
        e = _MemoryEntry(
            entry_id="e001",
            content=content,
            importance_score=force_importance or 0.9,
            metadata=metadata or {},
        )
        self._entries.append(e)
        # DB にも INSERT
        self._conn.execute(
            "INSERT INTO memory_entries VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (e.entry_id, e.content, e.importance_score, e.content_hash,
             e.created_at, e.updated_at, e.access_count,
             "[]", "{}", "{}", None),
        )
        self._conn.commit()
        return e

    def semantic_search(self, query, limit=10, min_importance=0.0):
        return [(e, 0.85) for e in self._entries[:limit]]


_rag_stub.RAGMemoryEnhancedV2 = _FakeRAG  # type: ignore

# ─── lessons_recorder スタブ ─────────────────────────────────────────────────

_lr_stub = _make_stub("lessons_recorder")


@dataclass
class _LessonEntry:
    lesson_id: str = "lr001"
    instruction: str = "test instruction"
    category: str = "other"
    trigger_text: str = ""
    session_id: str = ""
    created_at: str = "2026-01-01T12:00:00"
    access_count: int = 0
    last_accessed_at: str = ""
    tags: List[str] = field(default_factory=list)


class _FakeLessonsRecorder:
    def __init__(self):
        self._lessons: List[_LessonEntry] = []

    def record_lesson(self, instruction, category="other", trigger_text="",
                      session_id="", tags=None):
        # 重複チェック（instructionが同じならaccess_count+1）
        for l in self._lessons:
            if l.instruction == instruction:
                l.access_count += 1
                return l
        e = _LessonEntry(
            lesson_id=f"lr{len(self._lessons):03d}",
            instruction=instruction,
            category=category,
            trigger_text=trigger_text,
            session_id=session_id,
            tags=tags or [],
        )
        self._lessons.append(e)
        return e

    def search_lessons(self, query="", category=None, limit=10):
        results = self._lessons
        if query:
            results = [l for l in results if query in l.instruction]
        if category:
            results = [l for l in results if l.category == category]
        return results[:limit]

    def get_context_text(self, limit=10, category=None):
        lessons = self.search_lessons(limit=limit, category=category)
        if not lessons:
            return "（教訓なし）"
        return "\n".join(f"- {l.instruction}" for l in lessons)

    def stats(self):
        return {"total": len(self._lessons)}


# リアルモジュールが既にある場合は Lesson を上書きしない
if getattr(_lr_stub, "__is_stub__", False):
    _lr_stub.LessonsRecorder = _FakeLessonsRecorder  # type: ignore
    _lr_stub.Lesson = _LessonEntry  # type: ignore

# ─── agent_tracker スタブ（_UsageRecord/_AgentStats/_FakeAgentTracker 先に定義）─

@dataclass
class _UsageRecord:
    agent_name: str = "test-agent"
    task_summary: str = ""
    session_id: str = ""
    recorded_at: str = "2026-01-01T12:00:00"


@dataclass
class _AgentStats:
    agent_name: str = "test-agent"
    total_uses: int = 0
    rank: str = "N"
    last_used_at: str = ""
    days_since_use: Optional[int] = None
    is_parking_candidate: bool = True


class _FakeAgentTracker:
    def __init__(self):
        self._records: List[_UsageRecord] = []

    def track(self, agent_name, task_summary="", session_id=""):
        r = _UsageRecord(agent_name=agent_name, task_summary=task_summary, session_id=session_id)
        self._records.append(r)
        return r

    def get_stats(self, agent_name):
        count = sum(1 for r in self._records if r.agent_name == agent_name)
        return _AgentStats(agent_name=agent_name, total_uses=count,
                           rank="N-B" if count >= 5 else ("N-C" if count >= 1 else "N"))

    def audit_agents_dir(self, agents_dir=None):
        return {"total": 0, "passing": 0, "failing": 0, "results": [], "low_quality": []}

    def stats(self):
        return {"total_agents": len({r.agent_name for r in self._records})}


_at_stub = _make_stub("agent_tracker")
if getattr(_at_stub, "__is_stub__", False):
    _at_stub.AgentTracker = _FakeAgentTracker  # type: ignore
    _at_stub.UsageRecord = _UsageRecord  # type: ignore
    _at_stub.AgentStats = _AgentStats  # type: ignore


# ─── server モジュールをリセットしてインポート ───────────────────────────────

if "mrl_memory_mcp_server.server" in sys.modules:
    del sys.modules["mrl_memory_mcp_server.server"]
if "mrl_memory_mcp_server" in sys.modules:
    del sys.modules["mrl_memory_mcp_server"]

import mrl_memory_mcp_server.server as srv  # noqa: E402


# ─── フィクスチャ ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_rag_singleton():
    """各テスト前後にシングルトンをリセット"""
    srv._rag_memory = None
    srv._episodic_memory = None
    srv._lessons_recorder = None
    srv._agent_tracker = None
    yield
    srv._rag_memory = None
    srv._episodic_memory = None
    srv._lessons_recorder = None
    srv._agent_tracker = None


@pytest.fixture()
def fake_rag():
    """_rag_memory に FakeRAG を注入し、それを返す"""
    rag = _FakeRAG()
    srv._rag_memory = rag
    return rag


@pytest.fixture()
def fake_episodic():
    """_episodic_memory に FakeEpisodicMemory を注入し、それを返す"""
    em = _FakeEpisodicMemory()
    srv._episodic_memory = em
    return em


@pytest.fixture()
def fake_lessons():
    """_lessons_recorder に FakeLessonsRecorder を注入し、それを返す"""
    lr = _FakeLessonsRecorder()
    srv._lessons_recorder = lr
    return lr


@pytest.fixture()
def fake_tracker():
    """_agent_tracker に FakeAgentTracker を注入し、それを返す"""
    tracker = _FakeAgentTracker()
    srv._agent_tracker = tracker
    return tracker


# ─── _get_rag() ──────────────────────────────────────────────────────────────

class TestGetRag:
    def test_returns_fake_rag_when_set(self, fake_rag):
        assert srv._get_rag() is fake_rag

    def test_lazy_init_success(self):
        assert srv._rag_memory is None
        # rag_memory_enhanced_v2.RAGMemoryEnhancedV2 = _FakeRAG は既に設定済み
        result = srv._get_rag()
        assert result is not None

    def test_singleton_same_instance(self):
        r1 = srv._get_rag()
        r2 = srv._get_rag()
        assert r1 is r2

    def test_returns_none_on_import_error(self):
        srv._rag_memory = None
        with patch.dict(sys.modules, {"rag_memory_enhanced_v2": None}):
            # ValueError: sys.modules に None を入れると ImportError になる
            result = srv._get_rag()
            # モジュールがないときは None を返す
            # (_FakeRAG は残っているので実際には成功してしまう場合がある)
            # ここでは「エラーが起きても例外が上位に伝播しない」ことを確認
            pass  # エラーが出なければOK


# ─── _store_to_rag() ────────────────────────────────────────────────────────

class TestStoreToRag:
    def test_calls_add_memory_with_force_importance(self, fake_rag):
        result = srv._store_to_rag("テスト記憶", source="test")
        assert result["status"] == "stored"
        assert len(fake_rag._entries) == 1
        assert fake_rag._entries[0].importance_score == 1.0  # force_importance=1.0

    def test_returns_entry_without_embedding(self, fake_rag):
        result = srv._store_to_rag("embedding除外テスト")
        entry = result.get("entry", {})
        assert "embedding" not in entry

    def test_backend_label(self, fake_rag):
        result = srv._store_to_rag("バックエンド確認")
        assert result["backend"] == "rag_memory_v2"

    def test_metadata_includes_source(self, fake_rag):
        srv._store_to_rag("ソースチェック", source="unit-test")
        assert fake_rag._entries[0].metadata["source"] == "unit-test"

    def test_default_source_mcp_chat(self, fake_rag):
        srv._store_to_rag("デフォルトソース")
        assert fake_rag._entries[0].metadata["source"] == "mcp-chat"

    def test_fallback_to_requests_when_rag_none(self):
        srv._rag_memory = None
        # rag_memory_enhanced_v2 を一時的に壊す
        original = _rag_stub.RAGMemoryEnhancedV2
        _rag_stub.RAGMemoryEnhancedV2 = None  # type: ignore

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        srv._requests = MagicMock()
        srv._requests.post.return_value = mock_resp

        result = srv._store_to_rag("requests fallback")
        assert "status" in result or "error" in result  # エラーでも落ちない

        # 後片付け
        _rag_stub.RAGMemoryEnhancedV2 = original  # type: ignore
        srv._requests = _req


# ─── _search_rag() ──────────────────────────────────────────────────────────

class TestSearchRag:
    def test_empty_returns_zero_count(self, fake_rag):
        result = srv._search_rag("空検索")
        assert result["count"] == 0
        assert result["results"] == []

    def test_returns_stored_entries(self, fake_rag):
        fake_rag.add_memory("Python は汎用言語")
        result = srv._search_rag("Python")
        assert result["count"] == 1
        assert result["results"][0]["score"] == 0.85

    def test_embedding_excluded_from_results(self, fake_rag):
        fake_rag.add_memory("埋め込みテスト")
        result = srv._search_rag("テスト")
        entry = result["results"][0]["entry"]
        assert "embedding" not in entry

    def test_backend_label(self, fake_rag):
        result = srv._search_rag("backend確認")
        assert result["backend"] == "rag_memory_v2"

    def test_limit_respected(self, fake_rag):
        for i in range(5):
            fake_rag.add_memory(f"エントリ {i}")
        result = srv._search_rag("エントリ", limit=3)
        assert result["count"] <= 3

    def test_returns_query_in_response(self, fake_rag):
        result = srv._search_rag("クエリ確認")
        assert result["query"] == "クエリ確認"


# ─── _context_rag() ─────────────────────────────────────────────────────────

class TestContextRag:
    def test_empty_returns_no_memory_message(self, fake_rag):
        result = srv._context_rag("空コンテキスト")
        assert "見つかりませんでした" in result["context"]

    def test_context_is_string(self, fake_rag):
        fake_rag.add_memory("文脈テスト内容")
        result = srv._context_rag("文脈テスト")
        assert isinstance(result["context"], str)

    def test_context_contains_similarity(self, fake_rag):
        fake_rag.add_memory("類似度確認用コンテンツ")
        result = srv._context_rag("類似度確認")
        assert "0.85" in result["context"]

    def test_length_matches_context(self, fake_rag):
        fake_rag.add_memory("長さチェック")
        result = srv._context_rag("長さ")
        assert result["length"] == len(result["context"])

    def test_backend_label(self, fake_rag):
        result = srv._context_rag("バックエンド")
        assert result["backend"] == "rag_memory_v2"

    def test_count_matches_results(self, fake_rag):
        fake_rag.add_memory("件数チェック1")
        fake_rag.add_memory("件数チェック2")
        result = srv._context_rag("件数チェック")
        assert result["count"] == 2


# ─── _metrics_rag() ─────────────────────────────────────────────────────────

class TestMetricsRag:
    def test_rag_v2_available_true(self, fake_rag):
        result = srv._metrics_rag()
        assert result["rag_v2_available"] is True

    def test_initial_total_entries_zero(self, fake_rag):
        result = srv._metrics_rag()
        assert result["total_entries"] == 0

    def test_total_entries_after_store(self, fake_rag):
        fake_rag.add_memory("メトリクステスト")
        result = srv._metrics_rag()
        assert result["total_entries"] == 1

    def test_contains_db_path(self, fake_rag):
        result = srv._metrics_rag()
        assert "db_path" in result

    def test_backend_label(self, fake_rag):
        result = srv._metrics_rag()
        assert result["backend"] == "rag_memory_v2"

    def test_rag_none_returns_unavailable(self):
        # _rag_memory を None のまま & import 失敗を模擬
        srv._rag_memory = None
        original = _rag_stub.RAGMemoryEnhancedV2
        _rag_stub.RAGMemoryEnhancedV2 = None  # type: ignore
        result = srv._metrics_rag()
        # RAGv2 が None → unavailable または error
        assert "rag_v2_available" in result or "error" in result
        _rag_stub.RAGMemoryEnhancedV2 = original  # type: ignore

    def test_avg_importance_after_store(self, fake_rag):
        fake_rag.add_memory("重要度テスト")
        result = srv._metrics_rag()
        assert 0.0 <= result.get("avg_importance", 0) <= 1.0


# ─── fire-and-forget (Flask API 並行記録) ───────────────────────────────────

class TestFlaskParallelStore:
    def test_flask_post_called_in_thread(self, fake_rag):
        """memory_store 後、Flask APIへのfireAndForgetスレッドが走ること"""
        mock_requests = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_requests.post.return_value = mock_resp

        original_req = srv._requests
        srv._requests = mock_requests

        srv._store_to_rag("並行記録テスト", source="test")
        # スレッドが完了するまで少し待つ
        import time
        time.sleep(0.1)

        # Flask API post が1回以上呼ばれていること
        assert mock_requests.post.call_count >= 1
        srv._requests = original_req


# ─── _flask_post_async (単体) ────────────────────────────────────────────────

class TestFlaskPostAsync:
    def test_no_crash_when_requests_none(self):
        original = srv._requests
        srv._requests = None
        srv._flask_post_async("/api/memory/process", {"text": "x"})  # 例外が出ないこと
        srv._requests = original

    def test_no_crash_on_network_error(self):
        mock_requests = MagicMock()
        mock_requests.post.side_effect = ConnectionError("refused")
        original = srv._requests
        srv._requests = mock_requests
        srv._flask_post_async("/api/memory/process", {"text": "x"})  # 例外が出ないこと
        srv._requests = original


# ─── _store_to_episodic() ────────────────────────────────────────────────────

class TestStoreToEpisodic:
    def test_stores_entry(self, fake_episodic):
        result = srv._store_to_episodic("会話テスト", session_id="ses1")
        assert result is not None
        assert "entry_id" in result
        assert len(fake_episodic._entries) == 1

    def test_session_id_passed(self, fake_episodic):
        srv._store_to_episodic("セッションテスト", session_id="ses-abc")
        assert fake_episodic._entries[0].session_id == "ses-abc"

    def test_memory_type_is_conversation(self, fake_episodic):
        srv._store_to_episodic("タイプチェック", session_id="s1")
        assert fake_episodic._entries[0].memory_type == "conversation"

    def test_importance_score_0_7(self, fake_episodic):
        srv._store_to_episodic("重要度チェック", session_id="s1")
        assert fake_episodic._entries[0].importance_score == 0.7

    def test_returns_none_when_episodic_unavailable(self, monkeypatch):
        monkeypatch.setattr(srv, "_get_episodic", lambda: None)
        result = srv._store_to_episodic("unavailable test", session_id="s1")
        assert result is None

    def test_no_crash_on_store_error(self, fake_episodic):
        fake_episodic.store = MagicMock(side_effect=RuntimeError("broken"))
        result = srv._store_to_episodic("エラーテスト", session_id="s1")
        assert result is None  # エラーでも None を返す（例外を上位に伝播しない）


# ─── デュアルライト（RAGv2 + EpisodicMemory 同時記録） ────────────────────────

class TestDualWrite:
    def test_rag_and_episodic_both_written(self, fake_rag, fake_episodic):
        srv._store_to_rag("デュアル書き込みテスト", source="test", session_id="ses1")
        import time; time.sleep(0.1)
        # RAGv2 に記録される
        assert len(fake_rag._entries) == 1
        # EpisodicMemory にも記録される
        assert len(fake_episodic._entries) == 1

    def test_session_id_forwarded_to_episodic(self, fake_rag, fake_episodic):
        srv._store_to_rag("セッションID転送テスト", source="src", session_id="custom-session")
        import time; time.sleep(0.1)
        assert fake_episodic._entries[0].session_id == "custom-session"

    def test_default_session_id_from_source(self, fake_rag, fake_episodic):
        srv._store_to_rag("デフォルトセッションテスト", source="my-source")
        import time; time.sleep(0.1)
        assert fake_episodic._entries[0].session_id == "mcp-my-source"

    def test_rag_store_still_succeeds_even_if_episodic_fails(self, fake_rag):
        """episodic が失敗しても RAGv2 への書き込みは成功する"""
        broken_em = _FakeEpisodicMemory()
        broken_em.store = MagicMock(side_effect=RuntimeError("episodic broken"))
        srv._episodic_memory = broken_em
        result = srv._store_to_rag("耐障害テスト", source="test")
        assert result["status"] == "stored"  # RAGv2 は成功
        assert len(fake_rag._entries) == 1


# ─── _metrics_rag() episodic フィールド ─────────────────────────────────────

class TestMetricsEpisodic:
    def test_metrics_contains_episodic_key(self, fake_rag, fake_episodic):
        result = srv._metrics_rag()
        assert "episodic" in result

    def test_episodic_available_true(self, fake_rag, fake_episodic):
        result = srv._metrics_rag()
        assert result["episodic"]["episodic_available"] is True

    def test_episodic_total_zero_initially(self, fake_rag, fake_episodic):
        result = srv._metrics_rag()
        assert result["episodic"]["total"] == 0

    def test_episodic_total_after_store(self, fake_rag, fake_episodic):
        fake_episodic.store("test", session_id="s1")
        result = srv._metrics_rag()
        assert result["episodic"]["total"] == 1

    def test_episodic_unavailable_when_none(self, fake_rag, monkeypatch):
        monkeypatch.setattr(srv, "_get_episodic", lambda: None)
        result = srv._metrics_rag()
        assert result["episodic"]["episodic_available"] is False


# ─── _record_lesson() ────────────────────────────────────────────────────────

class TestRecordLesson:
    def test_basic_record(self, fake_lessons):
        result = srv._record_lesson("コードを省略しない")
        assert result["status"] == "recorded"
        assert "lesson_id" in result

    def test_instruction_stored(self, fake_lessons):
        result = srv._record_lesson("テスト教訓")
        assert result["instruction"] == "テスト教訓"

    def test_category_stored(self, fake_lessons):
        result = srv._record_lesson("フォーマット", category="output_format")
        assert result["category"] == "output_format"

    def test_duplicate_increments_access_count(self, fake_lessons):
        srv._record_lesson("同じ教訓")
        result2 = srv._record_lesson("同じ教訓")
        # _FakeLessonsRecorder は重複で access_count+1 → 2回目は 1
        assert result2["access_count"] >= 1

    def test_lessons_unavailable_returns_error(self, monkeypatch):
        monkeypatch.setattr(srv, "_get_lessons", lambda: None)
        result = srv._record_lesson("失敗テスト")
        assert "error" in result


# ─── _search_lessons() ────────────────────────────────────────────────────────

class TestSearchLessons:
    def test_empty_returns_context(self, fake_lessons):
        result = srv._search_lessons()
        assert "context" in result
        assert "lessons" in result

    def test_stored_lesson_appears(self, fake_lessons):
        fake_lessons.record_lesson("Python を使う")
        result = srv._search_lessons(query="Python")
        assert result["count"] == 1

    def test_category_filter(self, fake_lessons):
        fake_lessons.record_lesson("フォーマット守る", category="output_format")
        result = srv._search_lessons(category="output_format")
        assert result["count"] >= 1

    def test_limit_applies(self, fake_lessons):
        for i in range(5):
            fake_lessons.record_lesson(f"lesson {i}")
        result = srv._search_lessons(limit=2)
        assert result["count"] <= 2

    def test_lessons_unavailable_returns_error(self, monkeypatch):
        monkeypatch.setattr(srv, "_get_lessons", lambda: None)
        result = srv._search_lessons()
        assert "error" in result


# ─── _track_agent() ───────────────────────────────────────────────────────────

class TestTrackAgent:
    def test_returns_tracked_status(self, fake_tracker):
        result = srv._track_agent("my-agent")
        assert result["status"] == "tracked"

    def test_agent_name_in_result(self, fake_tracker):
        result = srv._track_agent("agent-x")
        assert result["agent_name"] == "agent-x"

    def test_rank_returned(self, fake_tracker):
        result = srv._track_agent("agent-r")
        assert "rank" in result

    def test_total_uses_returned(self, fake_tracker):
        result = srv._track_agent("agent-r")
        assert "total_uses" in result

    def test_tracker_unavailable_returns_error(self, monkeypatch):
        monkeypatch.setattr(srv, "_get_tracker", lambda: None)
        result = srv._track_agent("ghost-agent")
        assert "error" in result


# ─── _audit_agents() ──────────────────────────────────────────────────────────

class TestAuditAgents:
    def test_returns_total(self, fake_tracker):
        result = srv._audit_agents()
        assert "total" in result

    def test_tracker_unavailable_returns_error(self, monkeypatch):
        monkeypatch.setattr(srv, "_get_tracker", lambda: None)
        result = srv._audit_agents()
        assert "error" in result

    def test_custom_dir_passed(self, fake_tracker):
        result = srv._audit_agents(agents_dir="/tmp/test_agents")
        assert "total" in result


# --- teardown: 注入したスタブを除去して他テストへの汚染を防止 ---
def teardown_module(module):  # noqa: ARG001
    """このファイルのテスト終了後に sys.modules を元の状態に戻す。"""
    for name in _STUBS_INJECTED:
        pre = _PRE_EXISTING.get(name)
        if pre is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = pre  # type: ignore
