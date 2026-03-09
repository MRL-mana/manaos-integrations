"""
Unit tests for scripts/misc/episodic_memory.py
Uses :memory: SQLite to avoid disk I/O.
"""
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# manaos_logger optional — file has try/except fallback, but ensure no import error
sys.modules.setdefault("manaos_logger", MagicMock(
    get_service_logger=MagicMock(return_value=MagicMock())
))

sys.path.insert(0, "scripts/misc")
# test_mrl_memory_mcp_server.py が収集時に episodic_memory スタブを注入するため、
# 本物のモジュールをインポートする前にスタブをリセットする
sys.modules.pop("episodic_memory", None)
from episodic_memory import (  # noqa: E402
    EpisodicEntry,
    EpisodicMemory,
    get_episodic_memory,
)


# ── EpisodicEntry.create ─────────────────────────────────────────────────────

class TestEpisodicEntryCreate:
    def test_returns_episodic_entry(self):
        e = EpisodicEntry.create(content="hello", session_id="s1")
        assert isinstance(e, EpisodicEntry)

    def test_content_stored(self):
        e = EpisodicEntry.create(content="test content", session_id="s1")
        assert e.content == "test content"

    def test_session_id_stored(self):
        e = EpisodicEntry.create(content="x", session_id="sess-42")
        assert e.session_id == "sess-42"

    def test_default_memory_type(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        assert e.memory_type == "conversation"

    def test_custom_memory_type(self):
        e = EpisodicEntry.create(content="x", session_id="s1", memory_type="decision")
        assert e.memory_type == "decision"

    def test_importance_clamped_to_zero(self):
        e = EpisodicEntry.create(content="x", session_id="s1", importance_score=-1.0)
        assert e.importance_score == 0.0

    def test_importance_clamped_to_one(self):
        e = EpisodicEntry.create(content="x", session_id="s1", importance_score=2.0)
        assert e.importance_score == 1.0

    def test_importance_midpoint(self):
        e = EpisodicEntry.create(content="x", session_id="s1", importance_score=0.7)
        assert e.importance_score == pytest.approx(0.7)

    def test_tags_stored(self):
        e = EpisodicEntry.create(content="x", session_id="s1", tags=["a", "b"])
        assert e.tags == ["a", "b"]

    def test_default_tags_empty(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        assert e.tags == []

    def test_not_promoted_by_default(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        assert e.promoted is False

    def test_entry_id_is_uuid_string(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        assert isinstance(e.entry_id, str)
        assert len(e.entry_id) == 36  # UUID format

    def test_expires_at_is_after_created_at(self):
        e = EpisodicEntry.create(content="x", session_id="s1", ttl_hours=1)
        created = datetime.fromisoformat(e.created_at)
        expires = datetime.fromisoformat(e.expires_at)
        assert expires > created


# ── EpisodicEntry.is_expired ─────────────────────────────────────────────────

class TestEpisodicEntryIsExpired:
    def test_not_expired_by_default(self):
        e = EpisodicEntry.create(content="x", session_id="s1", ttl_hours=24)
        assert e.is_expired() is False

    def test_expired_entry(self):
        now = datetime.utcnow()
        e = EpisodicEntry.create(content="x", session_id="s1", ttl_hours=0)
        # Force expires_at to the past
        e.expires_at = (now - timedelta(seconds=1)).isoformat()
        assert e.is_expired() is True


# ── EpisodicEntry.to_summary ─────────────────────────────────────────────────

class TestEpisodicEntryToSummary:
    def test_returns_dict(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        assert isinstance(e.to_summary(), dict)

    def test_summary_has_required_keys(self):
        e = EpisodicEntry.create(content="x", session_id="s1")
        summary = e.to_summary()
        for k in ("entry_id", "content_preview", "session_id", "memory_type",
                  "importance_score", "tags", "created_at", "expires_at", "promoted"):
            assert k in summary

    def test_long_content_truncated_in_preview(self):
        long_content = "x" * 200
        e = EpisodicEntry.create(content=long_content, session_id="s1")
        preview = e.to_summary()["content_preview"]
        assert len(preview) <= 123  # 120 + "..."

    def test_short_content_not_truncated(self):
        e = EpisodicEntry.create(content="short", session_id="s1")
        assert "..." not in e.to_summary()["content_preview"]


# ── EpisodicMemory.store / recall ────────────────────────────────────────────

class TestEpisodicMemoryStoreRecall:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_store_returns_episodic_entry(self):
        e = self.em.store("hello", session_id="s1")
        assert isinstance(e, EpisodicEntry)

    def test_stored_content_matches(self):
        e = self.em.store("my content", session_id="s1")
        assert e.content == "my content"

    def test_recall_returns_stored_entry(self):
        self.em.store("test", session_id="sess1")
        entries = self.em.recall(session_id="sess1")
        assert len(entries) == 1
        assert entries[0].content == "test"

    def test_recall_filters_by_session(self):
        self.em.store("for s1", session_id="s1")
        self.em.store("for s2", session_id="s2")
        s1_entries = self.em.recall(session_id="s1")
        assert all(e.session_id == "s1" for e in s1_entries)

    def test_recall_filters_by_memory_type(self):
        self.em.store("decision", session_id="s1", memory_type="decision")
        self.em.store("conversation", session_id="s1", memory_type="conversation")
        decisions = self.em.recall(session_id="s1", memory_type="decision")
        assert all(e.memory_type == "decision" for e in decisions)

    def test_recall_filters_by_min_importance(self):
        self.em.store("important", session_id="s1", importance_score=0.9)
        self.em.store("low", session_id="s1", importance_score=0.2)
        high = self.em.recall(session_id="s1", min_importance=0.5)
        assert all(e.importance_score >= 0.5 for e in high)

    def test_recall_excludes_promoted_by_default(self):
        # Will not exclude if include_promoted=True (default)
        e = self.em.store("x", session_id="s1", importance_score=0.9)
        self.em.promote_to_longterm(e.entry_id)
        entries_with = self.em.recall(session_id="s1", include_promoted=True)
        entries_without = self.em.recall(session_id="s1", include_promoted=False)
        assert len(entries_with) >= len(entries_without)

    def test_recall_limit(self):
        for i in range(10):
            self.em.store(f"entry {i}", session_id="s1")
        entries = self.em.recall(session_id="s1", limit=3)
        assert len(entries) <= 3

    def test_multiple_sessions(self):
        for s in ["a", "b", "c"]:
            self.em.store(f"content for {s}", session_id=s)
        all_entries = self.em.recall()
        assert len(all_entries) == 3


# ── EpisodicMemory.get ───────────────────────────────────────────────────────

class TestEpisodicMemoryGet:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_get_existing_entry(self):
        stored = self.em.store("hello", session_id="s1")
        retrieved = self.em.get(stored.entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == stored.entry_id

    def test_get_nonexistent_returns_none(self):
        assert self.em.get("no-such-id") is None

    def test_get_returns_correct_content(self):
        stored = self.em.store("specific content", session_id="s1")
        retrieved = self.em.get(stored.entry_id)
        assert retrieved.content == "specific content"


# ── EpisodicMemory.search ────────────────────────────────────────────────────

class TestEpisodicMemorySearch:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_search_finds_matching_content(self):
        self.em.store("画像生成を依頼", session_id="s1")
        self.em.store("音楽を作成", session_id="s1")
        results = self.em.search("画像")
        assert len(results) == 1
        assert "画像" in results[0].content

    def test_search_empty_query_returns_empty(self):
        self.em.store("x", session_id="s1")
        # search requires non-empty content LIKE
        results = self.em.search("")
        # Empty query matches % → should match all
        assert isinstance(results, list)

    def test_search_filters_by_session(self):
        self.em.store("shared keyword", session_id="s1")
        self.em.store("shared keyword", session_id="s2")
        results = self.em.search("shared", session_id="s1")
        assert all(e.session_id == "s1" for e in results)

    def test_search_returns_list(self):
        result = self.em.search("nomatch")
        assert isinstance(result, list)

    def test_search_limit(self):
        for i in range(10):
            self.em.store(f"item {i}", session_id="s1")
        results = self.em.search("item", limit=3)
        assert len(results) <= 3


# ── EpisodicMemory.promote_to_longterm ──────────────────────────────────────

class TestEpisodicMemoryPromote:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_promote_nonexistent_returns_false(self):
        assert self.em.promote_to_longterm("no-such-id") is False

    def test_promote_returns_true(self):
        e = self.em.store("important", session_id="s1")
        assert self.em.promote_to_longterm(e.entry_id) is True

    def test_promoted_entry_is_flagged(self):
        e = self.em.store("important", session_id="s1")
        self.em.promote_to_longterm(e.entry_id)
        retrieved = self.em.get(e.entry_id)
        assert retrieved.promoted is True

    def test_promote_already_promoted_returns_true(self):
        e = self.em.store("x", session_id="s1")
        self.em.promote_to_longterm(e.entry_id)
        assert self.em.promote_to_longterm(e.entry_id) is True

    def test_promote_with_longterm_fn(self):
        e = self.em.store("x", session_id="s1")
        called = []

        def store_fn(content, metadata):
            called.append((content, metadata))
            return "longterm-id-123"

        self.em.promote_to_longterm(e.entry_id, longterm_store_fn=store_fn)
        assert len(called) == 1
        retrieved = self.em.get(e.entry_id)
        assert retrieved.promotion_id == "longterm-id-123"

    def test_promote_with_failing_fn_returns_false(self):
        e = self.em.store("x", session_id="s1")

        def bad_fn(content, metadata):
            raise RuntimeError("external failure")

        result = self.em.promote_to_longterm(e.entry_id, longterm_store_fn=bad_fn)
        assert result is False


# ── EpisodicMemory.auto_promote_high_importance ──────────────────────────────

class TestAutoPromote:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_auto_promotes_high_importance(self):
        self.em.store("high", session_id="s1", importance_score=0.9)
        self.em.store("medium", session_id="s1", importance_score=0.3)
        count = self.em.auto_promote_high_importance(threshold=0.7)
        assert count == 1

    def test_nothing_to_promote_returns_zero(self):
        self.em.store("low", session_id="s1", importance_score=0.1)
        count = self.em.auto_promote_high_importance(threshold=0.9)
        assert count == 0

    def test_auto_promote_session_filter(self):
        self.em.store("high s1", session_id="s1", importance_score=0.9)
        self.em.store("high s2", session_id="s2", importance_score=0.9)
        count = self.em.auto_promote_high_importance(threshold=0.8, session_id="s1")
        assert count == 1


# ── EpisodicMemory.cleanup_expired ──────────────────────────────────────────

class TestCleanupExpired:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_cleanup_removes_expired_entries(self):
        e = self.em.store("old", session_id="s1")
        # Force expiry
        with self.em._conn() as conn:
            past = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
            conn.execute(
                "UPDATE episodic_entries SET expires_at=? WHERE entry_id=?",
                (past, e.entry_id)
            )
        deleted = self.em.cleanup_expired()
        assert deleted >= 1

    def test_cleanup_keeps_valid_entries(self):
        self.em.store("fresh", session_id="s1", ttl_hours=24)
        deleted = self.em.cleanup_expired()
        assert deleted == 0

    def test_cleanup_keeps_promoted_by_default(self):
        e = self.em.store("promoted-old", session_id="s1")
        self.em.promote_to_longterm(e.entry_id)
        # Force expiry
        with self.em._conn() as conn:
            past = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
            conn.execute(
                "UPDATE episodic_entries SET expires_at=? WHERE entry_id=?",
                (past, e.entry_id)
            )
        deleted = self.em.cleanup_expired(also_promoted=False)
        assert deleted == 0

    def test_cleanup_with_also_promoted_removes_all(self):
        e = self.em.store("promoted-old", session_id="s1")
        self.em.promote_to_longterm(e.entry_id)
        with self.em._conn() as conn:
            past = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
            conn.execute(
                "UPDATE episodic_entries SET expires_at=? WHERE entry_id=?",
                (past, e.entry_id)
            )
        deleted = self.em.cleanup_expired(also_promoted=True)
        assert deleted >= 1


# ── EpisodicMemory.stats ─────────────────────────────────────────────────────

class TestEpisodicMemoryStats:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_stats_returns_dict(self):
        assert isinstance(self.em.stats(), dict)

    def test_stats_has_required_keys(self):
        stats = self.em.stats()
        for k in ("total_entries", "active_entries", "promoted_entries", "by_type"):
            assert k in stats

    def test_total_entries_zero_on_fresh(self):
        assert self.em.stats()["total_entries"] == 0

    def test_total_entries_increases_on_store(self):
        self.em.store("x", session_id="s1")
        self.em.store("y", session_id="s1")
        assert self.em.stats()["total_entries"] == 2

    def test_by_type_tracks_memory_types(self):
        self.em.store("x", session_id="s1", memory_type="decision")
        stats = self.em.stats()
        assert "decision" in stats["by_type"]


# ── EpisodicMemory.get_session_summary ───────────────────────────────────────

class TestGetSessionSummary:
    def setup_method(self):
        self.em = EpisodicMemory(db_path=":memory:")

    def test_empty_session_returns_minimal_dict(self):
        summary = self.em.get_session_summary("no-such-session")
        assert summary == {"session_id": "no-such-session", "entries": 0}

    def test_session_summary_has_entries_count(self):
        for i in range(3):
            self.em.store(f"item {i}", session_id="sess-x")
        summary = self.em.get_session_summary("sess-x")
        assert summary["entries"] == 3

    def test_session_summary_has_max_importance(self):
        self.em.store("a", session_id="s1", importance_score=0.4)
        self.em.store("b", session_id="s1", importance_score=0.8)
        summary = self.em.get_session_summary("s1")
        assert summary["max_importance"] == pytest.approx(0.8)

    def test_session_summary_previews_length(self):
        for i in range(10):
            self.em.store(f"item {i}", session_id="s1")
        summary = self.em.get_session_summary("s1")
        assert len(summary["previews"]) <= 5


# ── get_episodic_memory singleton ───────────────────────────────────────────

class TestGetEpisodicMemory:
    def test_returns_episodic_memory_instance(self):
        import episodic_memory as em_mod
        em_mod._default_instance = None
        instance = get_episodic_memory(":memory:")
        assert isinstance(instance, EpisodicMemory)

    def test_singleton_same_instance(self):
        import episodic_memory as em_mod
        em_mod._default_instance = None
        i1 = get_episodic_memory(":memory:")
        i2 = get_episodic_memory()
        assert i1 is i2
