"""
Unit tests for scripts/misc/rag_memory_enhanced_v2.py
Pure-method tests (no network, no real DB).
"""
import sys
import math
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"api_call": 10.0})
sys.modules.setdefault("manaos_timeout_config", _tc)

# database_connection_pool mock — get_pool returns a mock pool
_pool_inst = MagicMock()

@contextmanager
def _fake_conn():
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    yield conn

_pool_inst.get_connection = _fake_conn
_dbcp = MagicMock()
_dbcp.get_pool = MagicMock(return_value=_pool_inst)
sys.modules.setdefault("database_connection_pool", _dbcp)

# unified_cache_system mock
_ucs = MagicMock()
_ucs.get_unified_cache = MagicMock(return_value=MagicMock())
sys.modules.setdefault("unified_cache_system", _ucs)

_paths = MagicMock()
_paths.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.rag_memory_enhanced_v2 import (
    MemoryEntry,
    RAGMemoryEnhancedV2,
)


@pytest.fixture
def rag(tmp_path):
    return RAGMemoryEnhancedV2(
        db_path=tmp_path / "rag_v2.db",
        ollama_url="http://127.0.0.1:11434",
    )


# ── TestMemoryEntry ───────────────────────────────────────────────────────
class TestMemoryEntry:
    def _entry(self, **kw):
        defaults = dict(
            entry_id="e1", content="test content", importance_score=0.7,
            content_hash="abc123", created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00", access_count=0,
            last_accessed_at="2026-01-01T00:00:00",
            related_entries=[], temporal_context={}, metadata={},
        )
        defaults.update(kw)
        return MemoryEntry(**defaults)

    def test_create(self):
        e = self._entry()
        assert e.entry_id == "e1"
        assert e.importance_score == 0.7

    def test_embedding_default_none(self):
        e = self._entry()
        assert e.embedding is None

    def test_embedding_set(self):
        e = self._entry(embedding=[0.1, 0.2, 0.3])
        assert len(e.embedding) == 3


# ── TestCosineSimilarity ──────────────────────────────────────────────────
class TestCosineSimilarity:
    def test_identical_vectors(self, rag):
        v = [1.0, 0.0, 0.0]
        assert rag._cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self, rag):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert rag._cosine_similarity(v1, v2) == pytest.approx(0.0)

    def test_opposite_vectors(self, rag):
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        assert rag._cosine_similarity(v1, v2) == pytest.approx(-1.0)

    def test_empty_vectors(self, rag):
        assert rag._cosine_similarity([], []) == 0.0

    def test_zero_magnitude(self, rag):
        assert rag._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_mismatched_length(self, rag):
        assert rag._cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_symmetric(self, rag):
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]
        assert rag._cosine_similarity(v1, v2) == pytest.approx(
            rag._cosine_similarity(v2, v1)
        )


# ── TestCalculateContentHash ──────────────────────────────────────────────
class TestCalculateContentHash:
    def test_returns_string(self, rag):
        h = rag._calculate_content_hash("hello")
        assert isinstance(h, str)

    def test_sha256_length(self, rag):
        h = rag._calculate_content_hash("hello")
        assert len(h) == 64

    def test_deterministic(self, rag):
        assert rag._calculate_content_hash("hello") == rag._calculate_content_hash("hello")

    def test_different_content(self, rag):
        assert rag._calculate_content_hash("hello") != rag._calculate_content_hash("world")


# ── TestCalculateImportanceScore ──────────────────────────────────────────
class TestCalculateImportanceScore:
    def test_base_score(self, rag):
        score = rag._calculate_importance_score("no keywords here")
        assert 0.0 <= score <= 1.0

    def test_importance_keyword_boosts(self, rag):
        base = rag._calculate_importance_score("plain text")
        with_kw = rag._calculate_importance_score("重要な設定変更")
        assert with_kw > base

    def test_high_priority_context(self, rag):
        base = rag._calculate_importance_score("content")
        with_ctx = rag._calculate_importance_score("content", context={"priority": "high"})
        assert with_ctx > base

    def test_error_context_boosts(self, rag):
        base = rag._calculate_importance_score("content")
        with_err = rag._calculate_importance_score("content", context={"type": "error"})
        assert with_err > base

    def test_score_clamped_to_one(self, rag):
        # many keywords should not exceed 1.0
        text = "重要 必須 必要 緊急 優先 完了 成功 失敗 エラー 設定"
        score = rag._calculate_importance_score(text, context={"priority": "high", "type": "error"})
        assert score <= 1.0

    def test_returns_float(self, rag):
        score = rag._calculate_importance_score("test")
        assert isinstance(score, float)
