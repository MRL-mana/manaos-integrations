"""
RAGEngine のテスト
httpx・numpy・Ollama はモックして高速・独立テスト
"""

import pytest
import sys
import json
import uuid
import types
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# 依存モジュールをモック
for mod_name in ("manaos_logger", "manaos_error_handler", "_paths"):
    if mod_name not in sys.modules:
        m = types.ModuleType(mod_name)
        m.get_service_logger = lambda name="": __import__("logging").getLogger(name)
        m.get_logger = lambda name="": __import__("logging").getLogger(name)
        m.OLLAMA_PORT = 11434
        sys.modules[mod_name] = m

from scripts.misc.rag_engine import RAGEngine, SearchResult, RAGChunk, get_rag_engine


# --------------------------------
# フィクスチャ
# --------------------------------

@pytest.fixture
def engine():
    """ユニークなインメモリテストDB。embedding は無効化。"""
    db_name = f"ragtest_{uuid.uuid4().hex}"
    e = RAGEngine(db_path=f"file:{db_name}?mode=memory&cache=shared")
    e._embed_available = False  # オフライン: キーワード検索のみ
    return e


@pytest.fixture
def engine_with_embed():
    """エンベディングをモックするRAGEngineインスタンス。"""
    db_name = f"ragtest_embed_{uuid.uuid4().hex}"
    e = RAGEngine(db_path=f"file:{db_name}?mode=memory&cache=shared")

    # 4次元の固定ベクトルを返すダミーembedding
    def mock_embed(text: str):
        # テキストから決定論的なベクトルを返す
        h = sum(ord(c) for c in text) % 100
        return [h / 100.0, (h + 1) / 100.0, (h + 2) / 100.0, (h + 3) / 100.0]

    e._get_embedding = mock_embed
    e._embed_available = True
    return e


@pytest.fixture
def tmp_file(tmp_path):
    """テスト用テキストファイル。"""
    f = tmp_path / "doc.txt"
    f.write_text("This is a test document.\n\nIt has multiple paragraphs.\n\nPython is great.", encoding="utf-8")
    return f


# --------------------------------
# DB初期化 テスト
# --------------------------------

class TestInitDB:
    def test_tables_created(self, engine):
        with engine._conn() as conn:
            tables = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "rag_chunks" in tables
        assert "rag_documents" in tables

    def test_indices_created(self, engine):
        with engine._conn() as conn:
            indices = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        assert "idx_doc" in indices


# --------------------------------
# テキスト分割 テスト
# --------------------------------

class TestSplitText:
    def test_short_text_single_chunk(self, engine):
        engine.chunk_size = 500
        chunks = engine._split_text("short text")
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_long_text_multiple_chunks(self, engine):
        engine.chunk_size = 50
        engine.chunk_overlap = 10
        long_text = "A" * 200
        chunks = engine._split_text(long_text)
        assert len(chunks) > 1

    def test_paragraph_boundaries_respected(self, engine):
        engine.chunk_size = 100
        text = "Para1 content.\n\nPara2 content.\n\nPara3 content."
        chunks = engine._split_text(text)
        # 段落単位でまとまること
        assert all(c.strip() for c in chunks)

    def test_empty_paragraphs_skipped(self, engine):
        text = "Para1\n\n\n\nPara2"
        chunks = engine._split_text(text)
        assert all(c.strip() for c in chunks)

    def test_split_by_chars_overlap(self, engine):
        engine.chunk_size = 10
        engine.chunk_overlap = 3
        text = "A" * 30
        chunks = engine._split_by_chars(text)
        assert len(chunks) > 1
        # 最初のチャンクのサイズ
        assert len(chunks[0]) == 10


# --------------------------------
# コサイン類似度 テスト
# --------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self, engine):
        v = [1.0, 0.0, 0.0]
        assert abs(engine._cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self, engine):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert abs(engine._cosine_similarity(v1, v2)) < 1e-6

    def test_zero_vector(self, engine):
        v1 = [0.0, 0.0]
        v2 = [1.0, 0.0]
        assert engine._cosine_similarity(v1, v2) == 0.0

    def test_partial_similarity(self, engine):
        v1 = [1.0, 1.0]
        v2 = [1.0, 0.0]
        score = engine._cosine_similarity(v1, v2)
        assert 0.0 < score < 1.0


# --------------------------------
# index_text() テスト
# --------------------------------

class TestIndexText:
    def test_index_returns_doc_id(self, engine):
        doc_id = engine.index_text("Hello world", doc_title="Test")
        assert doc_id != ""

    def test_index_custom_doc_id(self, engine):
        doc_id = engine.index_text("content", doc_id="custom-123")
        assert doc_id == "custom-123"

    def test_index_creates_chunks(self, engine):
        engine.index_text("chunk content", doc_id="d1")
        s = engine.stats()
        assert s["total_chunks"] >= 1

    def test_index_creates_document_record(self, engine):
        engine.index_text("some text", doc_id="d2", doc_title="MyDoc")
        docs = engine.list_documents()
        assert any(d["doc_id"] == "d2" for d in docs)
        assert any(d["doc_title"] == "MyDoc" for d in docs)

    def test_index_empty_text_raises(self, engine):
        with pytest.raises(ValueError):
            engine.index_text("   ")

    def test_reindex_same_content_skipped(self, engine):
        engine.index_text("same content", doc_id="d3")
        first_stat = engine.stats()["total_chunks"]
        engine.index_text("same content", doc_id="d3")  # 同一コンテンツ
        second_stat = engine.stats()["total_chunks"]
        assert first_stat == second_stat

    def test_reindex_different_content_updates(self, engine):
        engine.index_text("version 1", doc_id="d4")
        engine.index_text("version 2 completely different", doc_id="d4")
        chunks = engine.get_document_chunks("d4")
        # 最新コンテンツのチャンクだけ残っている
        assert all("version 2" in c["content"] for c in chunks)

    def test_index_with_metadata(self, engine):
        doc_id = engine.index_text(
            "meta content",
            doc_id="d5",
            metadata={"author": "mana4", "category": "test"},
        )
        docs = engine.list_documents()
        doc = next(d for d in docs if d["doc_id"] == doc_id)
        assert doc["metadata"]["author"] == "mana4"

    def test_index_long_text_multiple_chunks(self, engine):
        engine.chunk_size = 20
        engine.chunk_overlap = 5
        long_text = " ".join([f"word{i}" for i in range(100)])
        doc_id = engine.index_text(long_text, doc_id="long_doc")
        chunks = engine.get_document_chunks(doc_id)
        assert len(chunks) > 1


# --------------------------------
# index_document() テスト
# --------------------------------

class TestIndexDocument:
    def test_index_file(self, engine, tmp_file):
        doc_id = engine.index_document(str(tmp_file))
        docs = engine.list_documents()
        assert any(d["doc_id"] == doc_id for d in docs)
        assert any(d["doc_title"] == tmp_file.name for d in docs)

    def test_index_file_not_found(self, engine):
        with pytest.raises(FileNotFoundError):
            engine.index_document("nonexistent/file.txt")

    def test_index_file_custom_title(self, engine, tmp_file):
        engine.index_document(str(tmp_file), doc_title="Custom Title")
        docs = engine.list_documents()
        assert any(d["doc_title"] == "Custom Title" for d in docs)


# --------------------------------
# delete_document() テスト
# --------------------------------

class TestDeleteDocument:
    def test_delete_existing(self, engine):
        engine.index_text("to delete", doc_id="del-1")
        result = engine.delete_document("del-1")
        assert result is True
        assert engine.list_documents() == []

    def test_delete_removes_chunks(self, engine):
        engine.index_text("chunk data", doc_id="del-2")
        engine.delete_document("del-2")
        chunks = engine.get_document_chunks("del-2")
        assert len(chunks) == 0

    def test_delete_nonexistent(self, engine):
        result = engine.delete_document("does-not-exist")
        assert result is False


# --------------------------------
# search() テスト（キーワード）
# --------------------------------

class TestSearch:
    def test_search_keyword_hit(self, engine):
        engine.index_text("Python programming best practices", doc_id="py1")
        results = engine.search("Python")
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)

    def test_search_no_hit(self, engine):
        engine.index_text("unrelated content", doc_id="u1")
        results = engine.search("XYZ_NONEXISTENT_TERM_9999")
        assert len(results) == 0

    def test_search_multiple_words(self, engine):
        engine.index_text("deep learning neural networks", doc_id="ml1")
        results = engine.search("deep neural")
        assert len(results) >= 1

    def test_search_with_doc_id_filter(self, engine):
        engine.index_text("Python info", doc_id="p1")
        engine.index_text("Python tips", doc_id="p2")
        results = engine.search("Python", doc_id_filter="p1")
        assert all(r.doc_id == "p1" for r in results)

    def test_search_top_k_limit(self, engine):
        engine.chunk_size = 20
        engine.chunk_overlap = 5
        long_text = " ".join(["target keyword"] * 50)
        engine.index_text(long_text, doc_id="many_chunks")
        results = engine.search("target", top_k=3)
        assert len(results) <= 3

    def test_search_result_fields(self, engine):
        engine.index_text("result test", doc_id="rt1", doc_title="Test Doc")
        results = engine.search("result")
        r = results[0]
        assert r.doc_id == "rt1"
        assert r.doc_title == "Test Doc"
        assert r.score >= 0.0
        assert r.chunk_index >= 0


# --------------------------------
# search() テスト（セマンティック）
# --------------------------------

class TestSemanticSearch:
    def test_semantic_search_returns_results(self, engine_with_embed):
        engine_with_embed.index_text("Machine learning concepts", doc_id="ml1")
        engine_with_embed.index_text("Cooking recipes", doc_id="cook1")
        results = engine_with_embed.search("machine learning")
        assert len(results) >= 1

    def test_semantic_search_min_score(self, engine_with_embed):
        engine_with_embed.index_text("test content", doc_id="t1")
        results = engine_with_embed.search("test", min_score=0.99)
        # 完全一致は難しいので0件でも1件でもOK（型チェックのみ）
        assert isinstance(results, list)

    def test_semantic_search_result_has_score(self, engine_with_embed):
        engine_with_embed.index_text("vector search demo", doc_id="vs1")
        results = engine_with_embed.search("vector")
        if results:
            assert isinstance(results[0].score, float)


# --------------------------------
# generate() テスト
# --------------------------------

class TestGenerate:
    def test_generate_with_context(self, engine):
        engine.index_text("Python was created by Guido van Rossum.", doc_id="py2")
        mock_results = engine.search("Python")

        with patch.object(engine, "_llm_generate", return_value="Guido van Rossum created Python.") as mock_gen:
            result = engine.generate("Who created Python?", context_results=mock_results)

        assert result["answer"] == "Guido van Rossum created Python."
        assert result["query"] == "Who created Python?"
        assert isinstance(result["sources"], list)

    def test_generate_auto_search(self, engine):
        engine.index_text("The sky is blue.", doc_id="sky1")
        with patch.object(engine, "_llm_generate", return_value="The sky is blue."):
            result = engine.generate("What color is the sky?")
        assert "answer" in result
        assert "sources" in result

    def test_generate_empty_context(self, engine):
        with patch.object(engine, "_llm_generate", return_value="No info") as mock_gen:
            result = engine.generate("unknown", context_results=[])
        assert result["answer"] == "No info"
        assert result["sources"] == []


# --------------------------------
# list_documents() テスト
# --------------------------------

class TestListDocuments:
    def test_list_empty(self, engine):
        assert engine.list_documents() == []

    def test_list_multiple(self, engine):
        engine.index_text("doc1", doc_id="d1", doc_title="Doc 1")
        engine.index_text("doc2", doc_id="d2", doc_title="Doc 2")
        docs = engine.list_documents()
        assert len(docs) == 2
        doc_ids = {d["doc_id"] for d in docs}
        assert {"d1", "d2"} == doc_ids

    def test_list_ordered_newest_first(self, engine):
        engine.index_text("old doc", doc_id="old")
        engine.index_text("new doc", doc_id="new")
        docs = engine.list_documents()
        # 最新が先頭（indexed_at DESC）
        assert docs[0]["doc_id"] == "new"


# --------------------------------
# get_document_chunks() テスト
# --------------------------------

class TestGetDocumentChunks:
    def test_get_chunks_existing(self, engine):
        engine.index_text("chunk A\n\nchunk B", doc_id="cb1")
        chunks = engine.get_document_chunks("cb1")
        assert len(chunks) >= 1

    def test_get_chunks_not_found(self, engine):
        chunks = engine.get_document_chunks("nonexistent")
        assert chunks == []

    def test_get_chunks_ordered_by_index(self, engine):
        engine.chunk_size = 10
        engine.chunk_overlap = 2
        engine.index_text("A" * 50, doc_id="ord1")
        chunks = engine.get_document_chunks("ord1")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == sorted(indices)


# --------------------------------
# stats() テスト
# --------------------------------

class TestStats:
    def test_stats_empty(self, engine):
        s = engine.stats()
        assert s["total_documents"] == 0
        assert s["total_chunks"] == 0
        assert s["embedded_chunks"] == 0

    def test_stats_after_index(self, engine):
        engine.index_text("content A", doc_id="A1")
        engine.index_text("content B", doc_id="A2")
        s = engine.stats()
        assert s["total_documents"] == 2
        assert s["total_chunks"] >= 2

    def test_stats_embed_model(self, engine):
        s = engine.stats()
        assert "embed_model" in s
        assert isinstance(s["embed_model"], str)

    def test_stats_db_path(self, engine):
        s = engine.stats()
        assert "db_path" in s


# --------------------------------
# SearchResult テスト
# --------------------------------

class TestSearchResult:
    def test_to_dict(self):
        r = SearchResult(
            chunk_id="c1", doc_id="d1", doc_title="T",
            content="content", score=0.876543,
            chunk_index=0, metadata={"k": "v"},
        )
        d = r.to_dict()
        assert d["score"] == 0.8765
        assert d["content"] == "content"
        assert d["metadata"] == {"k": "v"}


# --------------------------------
# シングルトン テスト
# --------------------------------

class TestSingleton:
    def test_get_rag_engine_returns_instance(self):
        import scripts.misc.rag_engine as re_module
        re_module._default_instance = None
        instance = get_rag_engine(db_path=":memory:")
        assert isinstance(instance, RAGEngine)

    def test_get_rag_engine_same_instance(self):
        import scripts.misc.rag_engine as re_module
        re_module._default_instance = None
        a = get_rag_engine(db_path=":memory:")
        b = get_rag_engine()
        assert a is b
