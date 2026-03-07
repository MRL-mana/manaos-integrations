"""
Unit tests for scripts/misc/rag_engine.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_paths = MagicMock()
_paths.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.rag_engine import (
    RAGChunk,
    RAGEngine,
    SearchResult,
    get_rag_engine,
)

# ── helpers ───────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """In-memory RAGEngine instance."""
    return RAGEngine(db_path=":memory:")


def _index_doc(engine: RAGEngine, doc_id: str = "doc1", title: str = "テストDoc", text: str = "テスト文書です。このテキストはRAGエンジンのテスト用です。") -> str:
    with patch.object(engine, "_get_embedding", return_value=None):
        return engine.index_text(text, doc_id=doc_id, doc_title=title)


# ── TestRAGChunk ──────────────────────────────────────────────────────────
class TestRAGChunk:
    def test_create(self):
        from datetime import datetime
        c = RAGChunk(
            chunk_id="c1",
            doc_id="d1",
            doc_title="Doc",
            content="Hello",
            chunk_index=0,
            embedding=[0.1, 0.2],
            metadata={},
            created_at=datetime.utcnow().isoformat(),
        )
        assert c.chunk_id == "c1"
        assert c.content == "Hello"
        assert c.embedding == [0.1, 0.2]


# ── TestSearchResult ──────────────────────────────────────────────────────
class TestSearchResult:
    def test_create(self):
        r = SearchResult("cid", "did", "title", "content", 0.9, 0, {})
        assert r.score == 0.9

    def test_to_dict(self):
        r = SearchResult("cid", "did", "title", "content", 0.87654, 0, {"k": "v"})
        d = r.to_dict()
        assert d["chunk_id"] == "cid"
        assert d["doc_id"] == "did"
        assert d["score"] == 0.8765
        assert d["metadata"] == {"k": "v"}


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_in_memory(self, engine):
        assert engine.db_path == ":memory:"

    def test_defaults(self, engine):
        assert engine.chunk_size == 500
        assert engine.chunk_overlap == 80

    def test_custom_params(self):
        e = RAGEngine(db_path=":memory:", chunk_size=200, chunk_overlap=20)
        assert e.chunk_size == 200
        assert e.chunk_overlap == 20


# ── TestInitDb ────────────────────────────────────────────────────────────
class TestInitDb:
    def test_tables_created(self, engine):
        with engine._conn() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "rag_chunks" in tables
        assert "rag_documents" in tables


# ── TestIndexText ─────────────────────────────────────────────────────────
class TestIndexText:
    def test_returns_doc_id(self, engine):
        doc_id = _index_doc(engine)
        assert doc_id == "doc1"

    def test_doc_stored(self, engine):
        _index_doc(engine, doc_id="storedoc")
        docs = engine.list_documents()
        assert any(d["doc_id"] == "storedoc" for d in docs)

    def test_auto_doc_id(self, engine):
        with patch.object(engine, "_get_embedding", return_value=None):
            doc_id = engine.index_text("hello world")
        assert doc_id  # UUID generated

    def test_empty_text_raises(self, engine):
        with pytest.raises(ValueError):
            engine.index_text("")

    def test_chunks_created(self, engine):
        _index_doc(engine, doc_id="chunkdoc")
        chunks = engine.get_document_chunks("chunkdoc")
        assert len(chunks) >= 1


# ── TestIndexTextIdempotent ───────────────────────────────────────────────
class TestIndexTextIdempotent:
    def test_same_content_skips_reindex(self, engine):
        text = "同じテキスト"
        with patch.object(engine, "_get_embedding", return_value=None) as m:
            engine.index_text(text, doc_id="idem1")
            engine.index_text(text, doc_id="idem1")
            # 2回目はスキップ → _get_embedding 呼ばれない
            assert m.call_count == 1  # 初回の1チャンクのみ


# ── TestDeleteDocument ────────────────────────────────────────────────────
class TestDeleteDocument:
    def test_delete_existing(self, engine):
        _index_doc(engine, doc_id="deldoc")
        result = engine.delete_document("deldoc")
        assert result is True
        assert not any(d["doc_id"] == "deldoc" for d in engine.list_documents())

    def test_delete_nonexistent(self, engine):
        result = engine.delete_document("notexist")
        assert result is False

    def test_chunks_also_deleted(self, engine):
        _index_doc(engine, doc_id="delchunkdoc")
        engine.delete_document("delchunkdoc")
        assert engine.get_document_chunks("delchunkdoc") == []


# ── TestListDocuments ─────────────────────────────────────────────────────
class TestListDocuments:
    def test_lists_all(self, engine):
        _index_doc(engine, doc_id="ld1")
        _index_doc(engine, doc_id="ld2", text="別のテキストです")
        docs = engine.list_documents()
        ids = [d["doc_id"] for d in docs]
        assert "ld1" in ids
        assert "ld2" in ids

    def test_empty(self, engine):
        assert engine.list_documents() == []


# ── TestGetDocumentChunks ─────────────────────────────────────────────────
class TestGetDocumentChunks:
    def test_returns_chunks(self, engine):
        _index_doc(engine, doc_id="getchunk")
        chunks = engine.get_document_chunks("getchunk")
        assert len(chunks) >= 1
        assert "content" in chunks[0]

    def test_missing_doc(self, engine):
        assert engine.get_document_chunks("notexist") == []


# ── TestStats ─────────────────────────────────────────────────────────────
class TestStats:
    def test_initial_empty(self, engine):
        s = engine.stats()
        assert s["total_documents"] == 0
        assert s["total_chunks"] == 0

    def test_after_index(self, engine):
        _index_doc(engine, doc_id="statdoc")
        s = engine.stats()
        assert s["total_documents"] == 1
        assert s["total_chunks"] >= 1

    def test_has_required_keys(self, engine):
        s = engine.stats()
        for k in ("total_documents", "total_chunks", "embedded_chunks", "unembedded_chunks", "embed_model"):
            assert k in s


# ── TestSplitText ─────────────────────────────────────────────────────────
class TestSplitText:
    def test_short_text_one_chunk(self, engine):
        chunks = engine._split_text("Short text")
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        e = RAGEngine(db_path=":memory:", chunk_size=50, chunk_overlap=10)
        long_text = "A" * 200
        chunks = e._split_text(long_text)
        assert len(chunks) > 1

    def test_paragraph_split(self, engine):
        text = "段落1\n\n段落2\n\n段落3"
        chunks = engine._split_text(text)
        assert len(chunks) >= 1

    def test_never_empty(self, engine):
        chunks = engine._split_text("x")
        assert len(chunks) >= 1
        assert all(c for c in chunks)


# ── TestSplitByChars ──────────────────────────────────────────────────────
class TestSplitByChars:
    def test_overlapping_chunks(self):
        e = RAGEngine(db_path=":memory:", chunk_size=10, chunk_overlap=3)
        text = "A" * 25
        chunks = e._split_by_chars(text)
        assert len(chunks) > 1
        # overlap: chunk N の末尾3文字 = chunk N+1 の先頭3文字
        assert chunks[1][:3] == chunks[0][-3:]


# ── TestCosineSimilarity ──────────────────────────────────────────────────
class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert abs(RAGEngine._cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        assert abs(RAGEngine._cosine_similarity([1, 0], [0, 1])) < 1e-6

    def test_zero_vector(self):
        assert RAGEngine._cosine_similarity([0, 0], [1, 2]) == 0.0


# ── TestKeywordSearch ─────────────────────────────────────────────────────
class TestKeywordSearch:
    def test_finds_matching(self, engine):
        _index_doc(engine, doc_id="kw1", text="Pythonの設定についての説明です")
        results = engine._keyword_search("Python", top_k=5, doc_id_filter=None)
        assert any(r.doc_id == "kw1" for r in results)

    def test_no_match(self, engine):
        _index_doc(engine, doc_id="kw2", text="Javaの説明です")
        results = engine._keyword_search("Rust", top_k=5, doc_id_filter=None)
        assert not any(r.doc_id == "kw2" for r in results)

    def test_empty_query(self, engine):
        results = engine._keyword_search("", top_k=5, doc_id_filter=None)
        assert results == []


# ── TestSearch ────────────────────────────────────────────────────────────
class TestSearch:
    def test_fallback_to_keyword(self, engine):
        _index_doc(engine, doc_id="s1", text="検索テスト文書")
        # embedding None → keyword fallback
        with patch.object(engine, "_get_embedding", return_value=None):
            results = engine.search("検索テスト")
        assert isinstance(results, list)

    def test_semantic_with_embeddings(self, engine):
        with patch.object(engine, "_get_embedding", return_value=[0.1, 0.9, 0.3]):
            engine.index_text("テスト文書", doc_id="sem1")
            results = engine.search("テスト")
        assert any(r.doc_id == "sem1" for r in results)


# ── TestGetRagEngine ──────────────────────────────────────────────────────
class TestGetRagEngine:
    def test_returns_instance(self, tmp_path, monkeypatch):
        import scripts.misc.rag_engine as re_mod
        monkeypatch.setattr(re_mod, "_default_instance", None)
        inst = get_rag_engine(db_path=str(tmp_path / "test.db"))
        assert isinstance(inst, RAGEngine)
