"""
EpisodicMemory のテスト
インメモリSQLite を使用して高速・独立テスト
"""

import pytest
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import types

# 依存モジュールをモック
for mod_name in ("manaos_logger", "manaos_error_handler"):
    if mod_name not in sys.modules:
        m = types.ModuleType(mod_name)
        m.get_service_logger = lambda name="": __import__("logging").getLogger(name)  # type: ignore
        m.get_logger = lambda name="": __import__("logging").getLogger(name)  # type: ignore
        sys.modules[mod_name] = m

from scripts.misc.episodic_memory import EpisodicEntry, EpisodicMemory, get_episodic_memory


# --------------------------------
# フィクスチャ
# --------------------------------

@pytest.fixture
def mem():
    """ユニークなインメモリテストDB（テスト間を完全隔離）"""
    db_name = f"eptest_{uuid.uuid4().hex}"
    return EpisodicMemory(db_path=f"file:{db_name}?mode=memory&cache=shared")


# --------------------------------
# EpisodicEntry テスト
# --------------------------------

class TestEpisodicEntry:
    def test_create_defaults(self):
        entry = EpisodicEntry.create("test content", session_id="s1")
        assert entry.content == "test content"
        assert entry.session_id == "s1"
        assert entry.memory_type == "conversation"
        assert 0.0 <= entry.importance_score <= 1.0
        assert isinstance(entry.tags, list)
        assert entry.promoted is False
        assert entry.promotion_id is None

    def test_create_custom_fields(self):
        entry = EpisodicEntry.create(
            "decision made",
            session_id="s2",
            memory_type="decision",
            importance_score=0.9,
            tags=["important", "action"],
            ttl_hours=2,
        )
        assert entry.memory_type == "decision"
        assert entry.importance_score == 0.9
        assert "important" in entry.tags

    def test_importance_score_clamp(self):
        e_high = EpisodicEntry.create("x", "s1", importance_score=1.5)
        e_low = EpisodicEntry.create("x", "s1", importance_score=-0.5)
        assert e_high.importance_score == 1.0
        assert e_low.importance_score == 0.0

    def test_is_expired_false(self):
        entry = EpisodicEntry.create("x", "s1", ttl_hours=24)
        assert entry.is_expired() is False

    def test_is_expired_true(self):
        entry = EpisodicEntry.create("x", "s1", ttl_hours=0)
        # ttl_hours=0 → 即期限切れ（expires_at = created_at + 0h）
        # 少し待ってから確認
        time.sleep(0.01)
        assert entry.is_expired() is True

    def test_to_summary_truncates_content(self):
        long_content = "a" * 200
        entry = EpisodicEntry.create(long_content, "s1")
        summary = entry.to_summary()
        assert len(summary["content_preview"]) <= 123  # 120 + "..."
        assert "..." in summary["content_preview"]

    def test_to_summary_short_content(self):
        entry = EpisodicEntry.create("short", "s1")
        summary = entry.to_summary()
        assert "..." not in summary["content_preview"]


# --------------------------------
# EpisodicMemory.store() テスト
# --------------------------------

class TestStore:
    def test_store_returns_entry(self, mem):
        entry = mem.store("hello", session_id="s1")
        assert entry.entry_id != ""
        assert entry.content == "hello"

    def test_store_default_importance(self, mem):
        entry = mem.store("hello", session_id="s1")
        assert entry.importance_score == 0.5

    def test_store_custom_importance(self, mem):
        entry = mem.store("critical", session_id="s1", importance_score=0.95)
        assert entry.importance_score == 0.95

    def test_store_with_tags(self, mem):
        entry = mem.store("tagged", session_id="s1", tags=["rag", "test"])
        retrieved = mem.get(entry.entry_id)
        assert retrieved is not None
        assert "rag" in retrieved.tags

    def test_store_multiple_entries(self, mem):
        for i in range(5):
            mem.store(f"content {i}", session_id="s1")
        results = mem.recall(session_id="s1")
        assert len(results) == 5


# --------------------------------
# EpisodicMemory.recall() テスト
# --------------------------------

class TestRecall:
    def test_recall_by_session(self, mem):
        mem.store("a1", session_id="sess-A")
        mem.store("b1", session_id="sess-B")
        mem.store("a2", session_id="sess-A")
        results = mem.recall(session_id="sess-A")
        assert all(r.session_id == "sess-A" for r in results)
        assert len(results) == 2

    def test_recall_by_type(self, mem):
        mem.store("conv", session_id="s1", memory_type="conversation")
        mem.store("dec", session_id="s1", memory_type="decision")
        results = mem.recall(memory_type="decision")
        assert all(r.memory_type == "decision" for r in results)

    def test_recall_min_importance(self, mem):
        mem.store("low", session_id="s1", importance_score=0.2)
        mem.store("high", session_id="s1", importance_score=0.8)
        results = mem.recall(min_importance=0.5)
        assert all(r.importance_score >= 0.5 for r in results)

    def test_recall_excludes_promoted_by_default(self, mem):
        e = mem.store("data", session_id="s1", importance_score=0.9)
        mem.promote_to_longterm(e.entry_id)  # no longterm_fn
        results = mem.recall(include_promoted=False)
        assert all(r.entry_id != e.entry_id for r in results)

    def test_recall_includes_promoted(self, mem):
        e = mem.store("data", session_id="s1", importance_score=0.9)
        mem.promote_to_longterm(e.entry_id)
        results = mem.recall(include_promoted=True)
        assert any(r.entry_id == e.entry_id for r in results)

    def test_recall_excludes_expired(self, mem):
        # expires_at を過去に手動設定する
        e = mem.store("expired_entry", session_id="s1")
        # DBを直接書き換えて期限切れにする
        with mem._conn() as conn:
            conn.execute(
                "UPDATE episodic_entries SET expires_at = ? WHERE entry_id = ?",
                ("2000-01-01T00:00:00", e.entry_id),
            )
        results = mem.recall(include_expired=False)
        assert all(r.entry_id != e.entry_id for r in results)

    def test_recall_includes_expired(self, mem):
        e = mem.store("exp_entry", session_id="s1")
        with mem._conn() as conn:
            conn.execute(
                "UPDATE episodic_entries SET expires_at = ? WHERE entry_id = ?",
                ("2000-01-01T00:00:00", e.entry_id),
            )
        results = mem.recall(include_expired=True)
        assert any(r.entry_id == e.entry_id for r in results)

    def test_recall_limit(self, mem):
        for i in range(10):
            mem.store(f"item {i}", session_id="s1")
        results = mem.recall(limit=3)
        assert len(results) <= 3

    def test_recall_order_newest_first(self, mem):
        mem.store("first", session_id="s1")
        time.sleep(0.01)
        mem.store("second", session_id="s1")
        results = mem.recall(session_id="s1")
        assert results[0].content == "second"


# --------------------------------
# EpisodicMemory.search() テスト
# --------------------------------

class TestSearch:
    def test_search_keyword_hit(self, mem):
        mem.store("Python の設定方法", session_id="s1")
        mem.store("ゲームの攻略", session_id="s1")
        results = mem.search("Python")
        assert len(results) == 1
        assert "Python" in results[0].content

    def test_search_no_hit(self, mem):
        mem.store("関係ない内容", session_id="s1")
        results = mem.search("XYZ_NOT_EXIST")
        assert len(results) == 0

    def test_search_by_session(self, mem):
        mem.store("Python info", session_id="A")
        mem.store("Python tips", session_id="B")
        results = mem.search("Python", session_id="A")
        assert all(r.session_id == "A" for r in results)

    def test_search_min_importance_filter(self, mem):
        mem.store("Python 高重要度", session_id="s1", importance_score=0.9)
        mem.store("Python 低重要度", session_id="s1", importance_score=0.1)
        results = mem.search("Python", min_importance=0.5)
        assert all(r.importance_score >= 0.5 for r in results)

    def test_search_excludes_expired(self, mem):
        e = mem.store("expired Python", session_id="s1")
        with mem._conn() as conn:
            conn.execute(
                "UPDATE episodic_entries SET expires_at = ? WHERE entry_id = ?",
                ("2000-01-01T00:00:00", e.entry_id),
            )
        results = mem.search("Python")
        assert all(r.entry_id != e.entry_id for r in results)


# --------------------------------
# EpisodicMemory.get() テスト
# --------------------------------

class TestGet:
    def test_get_existing(self, mem):
        e = mem.store("hello", session_id="s1")
        retrieved = mem.get(e.entry_id)
        assert retrieved is not None
        assert retrieved.content == "hello"

    def test_get_not_found(self, mem):
        assert mem.get("nonexistent-id") is None


# --------------------------------
# EpisodicMemory.promote_to_longterm() テスト
# --------------------------------

class TestPromote:
    def test_promote_no_fn_sets_flag(self, mem):
        e = mem.store("important data", session_id="s1", importance_score=0.9)
        result = mem.promote_to_longterm(e.entry_id)
        assert result is True
        promoted = mem.get(e.entry_id)
        assert promoted.promoted is True
        assert promoted.promotion_id is not None

    def test_promote_with_fn(self, mem):
        e = mem.store("data", session_id="s1")
        store_fn = MagicMock(return_value="lt-123")
        result = mem.promote_to_longterm(e.entry_id, store_fn)
        assert result is True
        assert store_fn.called
        promoted = mem.get(e.entry_id)
        assert promoted.promotion_id == "lt-123"

    def test_promote_fn_called_with_correct_metadata(self, mem):
        e = mem.store("data", session_id="sess-X", memory_type="decision")
        captured = {}

        def store_fn(content, metadata):
            captured["content"] = content
            captured["metadata"] = metadata
            return "lt-001"

        mem.promote_to_longterm(e.entry_id, store_fn)
        assert captured["content"] == "data"
        assert captured["metadata"]["session_id"] == "sess-X"
        assert captured["metadata"]["memory_type"] == "decision"

    def test_promote_idempotent(self, mem):
        e = mem.store("data", session_id="s1")
        mem.promote_to_longterm(e.entry_id)
        result = mem.promote_to_longterm(e.entry_id)  # 2回目
        assert result is True

    def test_promote_not_found(self, mem):
        result = mem.promote_to_longterm("nonexistent")
        assert result is False

    def test_promote_fn_error_returns_false(self, mem):
        e = mem.store("data", session_id="s1")

        def broken_fn(content, metadata):
            raise RuntimeError("broken")

        result = mem.promote_to_longterm(e.entry_id, broken_fn)
        assert result is False

    def test_auto_promote_high_importance(self, mem):
        mem.store("low", session_id="s1", importance_score=0.3)
        mem.store("high1", session_id="s1", importance_score=0.8)
        mem.store("high2", session_id="s1", importance_score=0.7)
        count = mem.auto_promote_high_importance(threshold=0.6)
        assert count == 2

    def test_auto_promote_skips_already_promoted(self, mem):
        e = mem.store("high", session_id="s1", importance_score=0.9)
        mem.promote_to_longterm(e.entry_id)
        count = mem.auto_promote_high_importance(threshold=0.5)
        assert count == 0


# --------------------------------
# EpisodicMemory.cleanup_expired() テスト
# --------------------------------

class TestCleanup:
    def _set_expired(self, mem, entry_id):
        with mem._conn() as conn:
            conn.execute(
                "UPDATE episodic_entries SET expires_at = ? WHERE entry_id = ?",
                ("2000-01-01T00:00:00", entry_id),
            )

    def test_cleanup_removes_expired(self, mem):
        e = mem.store("expired", session_id="s1")
        active = mem.store("active", session_id="s1")
        self._set_expired(mem, e.entry_id)
        deleted = mem.cleanup_expired()
        assert deleted == 1
        assert mem.get(e.entry_id) is None
        assert mem.get(active.entry_id) is not None

    def test_cleanup_keeps_promoted_by_default(self, mem):
        e = mem.store("promoted_expired", session_id="s1")
        self._set_expired(mem, e.entry_id)
        mem.promote_to_longterm(e.entry_id)
        deleted = mem.cleanup_expired(also_promoted=False)
        assert deleted == 0
        assert mem.get(e.entry_id) is not None

    def test_cleanup_also_promoted_deletes_all(self, mem):
        e = mem.store("promoted_expired", session_id="s1")
        self._set_expired(mem, e.entry_id)
        mem.promote_to_longterm(e.entry_id)
        deleted = mem.cleanup_expired(also_promoted=True)
        assert deleted == 1
        assert mem.get(e.entry_id) is None

    def test_cleanup_nothing_to_delete(self, mem):
        mem.store("active", session_id="s1")
        deleted = mem.cleanup_expired()
        assert deleted == 0


# --------------------------------
# EpisodicMemory.stats() テスト
# --------------------------------

class TestStats:
    def test_stats_empty(self, mem):
        s = mem.stats()
        assert s["total_entries"] == 0
        assert s["active_entries"] == 0

    def test_stats_counts(self, mem):
        mem.store("a", session_id="s1", memory_type="conversation")
        mem.store("b", session_id="s1", memory_type="decision")
        s = mem.stats()
        assert s["total_entries"] == 2
        assert s["active_entries"] == 2
        assert "conversation" in s["by_type"]
        assert "decision" in s["by_type"]

    def test_stats_avg_importance(self, mem):
        mem.store("a", session_id="s1", importance_score=0.4)
        mem.store("b", session_id="s1", importance_score=0.6)
        s = mem.stats()
        assert abs(s["avg_importance_active"] - 0.5) < 0.01

    def test_stats_promoted_count(self, mem):
        e = mem.store("data", session_id="s1")
        mem.promote_to_longterm(e.entry_id)
        s = mem.stats()
        assert s["promoted_entries"] == 1


# --------------------------------
# EpisodicMemory.get_session_summary() テスト
# --------------------------------

class TestSessionSummary:
    def test_no_entries_returns_minimal(self, mem):
        result = mem.get_session_summary("nonexistent")
        assert result["entries"] == 0

    def test_summary_with_entries(self, mem):
        mem.store("entry1", session_id="S1", importance_score=0.7, memory_type="conversation")
        mem.store("entry2", session_id="S1", importance_score=0.3, memory_type="decision")
        result = mem.get_session_summary("S1")
        assert result["entries"] == 2
        assert "conversation" in result["types"] or "decision" in result["types"]
        assert result["max_importance"] == 0.7


# --------------------------------
# シングルトン テスト
# --------------------------------

class TestSingleton:
    def test_get_episodic_memory_returns_instance(self):
        import scripts.misc.episodic_memory as em_module
        em_module._default_instance = None  # リセット
        instance = get_episodic_memory(db_path=":memory:")
        assert isinstance(instance, EpisodicMemory)

    def test_get_episodic_memory_same_instance(self):
        import scripts.misc.episodic_memory as em_module
        em_module._default_instance = None
        a = get_episodic_memory(db_path=":memory:")
        b = get_episodic_memory()
        assert a is b
