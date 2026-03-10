"""
RAGエンジン（Retrieval-Augmented Generation）
==============================================
ドキュメントをチャンク分割 → ベクトル化 → SQLite に保存し、
セマンティック検索とコンテキスト生成を提供する軽量RAGレイヤー。

既存の `rag_memory_enhanced_v2.py` がエージェント記憶向けなのに対し、
このモジュールは **任意のドキュメント**（ファイル・テキスト・会話ログ等）
をインデックスしてコンテキスト付きで取得することに特化。

バックエンド:
  - ベクトルストア: SQLite + numpy cosine similarity（依存を最小化）
  - エンベディング: Ollama（ローカル, mxbai-embed-large / nomic-embed-text 等）
                   or fallback として TF-IDF 近似
  - LLM生成: Ollama（オプション; search のみでも使用可）

使い方:
    rag = RAGEngine()
    doc_id = rag.index_document("path/to/file.txt")
    doc_id = rag.index_text("some long text...", doc_id="custom-id")
    results = rag.search("Pythonの設定について")
    answer  = rag.generate("Pythonの設定は？", context_results=results)
    rag.delete_document(doc_id)
"""

import os
import json
import sqlite3
import uuid
import math
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# ベクトル演算は numpy なしでもスカラー積で近似
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# HTTP クライアント（Ollama embedding）
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ロガー
try:
    from manaos_logger import get_service_logger
    logger = get_service_logger("rag-engine")
except Exception:
    import logging
    logger = logging.getLogger("rag-engine")

# パス設定
try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

# --------------------------------
# 設定定数
# --------------------------------

DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))         # 文字数
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))    # オーバーラップ文字数
DEFAULT_EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "mxbai-embed-large")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
DEFAULT_DB_PATH = os.getenv(
    "RAG_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "rag_engine.db"),
)
DEFAULT_TOP_K = 5
EMBED_TIMEOUT = float(os.getenv("RAG_EMBED_TIMEOUT", "30"))


# --------------------------------
# データクラス（軽量実装）
# --------------------------------

class RAGChunk:
    """RAGインデックスの1チャンク"""
    __slots__ = (
        "chunk_id", "doc_id", "doc_title", "content",
        "chunk_index", "embedding", "metadata", "created_at",
    )

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        doc_title: str,
        content: str,
        chunk_index: int,
        embedding: Optional[List[float]],
        metadata: Dict[str, Any],
        created_at: str,
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.doc_title = doc_title
        self.content = content
        self.chunk_index = chunk_index
        self.embedding = embedding
        self.metadata = metadata
        self.created_at = created_at


class SearchResult:
    """検索結果の1件"""
    __slots__ = ("chunk_id", "doc_id", "doc_title", "content", "score", "chunk_index", "metadata")

    def __init__(self, chunk_id, doc_id, doc_title, content, score, chunk_index, metadata):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.doc_title = doc_title
        self.content = content
        self.score = score
        self.chunk_index = chunk_index
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "content": self.content,
            "score": round(self.score, 4),
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


# --------------------------------
# メインクラス
# --------------------------------

class RAGEngine:
    """
    軽量RAGエンジン

    外部依存:
      - httpx   : Ollama API 呼び出し（オプション）
      - numpy   : コサイン類似度高速化（オプション）
      - sqlite3 : 標準ライブラリ（必須）
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        embed_model: str = DEFAULT_EMBED_MODEL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        raw = db_path or DEFAULT_DB_PATH
        # file: URI や :memory: は Path 変換せずそのまま保持
        if raw == ":memory:" or raw.startswith("file:"):
            self.db_path = raw
            self._persistent_conn: Optional[sqlite3.Connection] = sqlite3.connect(
                raw, uri=True, check_same_thread=False, timeout=15
            )
            self._persistent_conn.row_factory = sqlite3.Row
        else:
            self.db_path = Path(raw)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._persistent_conn = None
        self.embed_model = embed_model
        self.ollama_url = ollama_url.rstrip("/")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._embed_available: Optional[bool] = None  # 遅延チェック
        self._init_db()

    # --------------------------------
    # DB 初期化
    # --------------------------------

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id    TEXT PRIMARY KEY,
                    doc_id      TEXT NOT NULL,
                    doc_title   TEXT NOT NULL DEFAULT '',
                    content     TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL DEFAULT 0,
                    embedding   TEXT,              -- JSON float array or NULL
                    metadata    TEXT NOT NULL DEFAULT '{}',
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc ON rag_chunks(doc_id)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    doc_id      TEXT PRIMARY KEY,
                    doc_title   TEXT NOT NULL DEFAULT '',
                    source      TEXT NOT NULL DEFAULT '',
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL DEFAULT '',
                    metadata    TEXT NOT NULL DEFAULT '{}',
                    indexed_at  TEXT NOT NULL
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        """接続を返す。インメモリの場合は永続接続を再利用。"""
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    # --------------------------------
    # ドキュメントインデックス
    # --------------------------------

    def index_document(
        self,
        path: str,
        doc_id: Optional[str] = None,
        doc_title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        encoding: str = "utf-8",
    ) -> str:
        """
        テキストファイルをインデックスする。

        Args:
            path: ファイルパス
            doc_id: ドキュメントID（Noneで自動生成）
            doc_title: タイトル（Noneでファイル名）
            metadata: 追加メタデータ
            encoding: ファイルエンコーディング

        Returns:
            doc_id
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        text = p.read_text(encoding=encoding, errors="replace")
        title = doc_title or p.name
        return self.index_text(
            text=text,
            doc_id=doc_id,
            doc_title=title,
            source=str(p.resolve()),
            metadata=metadata,
        )

    def index_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
        doc_title: str = "",
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        テキストをチャンク分割してインデックスする。

        Args:
            text: インデックスするテキスト
            doc_id: ドキュメントID（Noneで自動生成）
            doc_title: ドキュメントタイトル
            source: ソース（ファイルパスやURL等）
            metadata: 追加メタデータ

        Returns:
            doc_id
        """
        if not text.strip():
            raise ValueError("text is empty")

        doc_id = doc_id or str(uuid.uuid4())
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        metadata = metadata or {}
        now = datetime.utcnow().isoformat()

        # 既存ドキュメントの重複チェック
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT doc_id, content_hash FROM rag_documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if existing and existing["content_hash"] == content_hash:
                logger.debug(f"[RAGEngine] doc unchanged, skip re-index: {doc_id}")
                return doc_id

        # 古いチャンクを削除（再インデックス）
        with self._conn() as conn:
            conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))

        # チャンク分割
        chunks = self._split_text(text)
        logger.info(f"[RAGEngine] indexing '{doc_title}' → {len(chunks)} chunks")

        # 各チャンクをベクトル化して保存
        for i, chunk_text in enumerate(chunks):
            embedding = self._get_embedding(chunk_text)
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO rag_chunks
                      (chunk_id, doc_id, doc_title, content, chunk_index,
                       embedding, metadata, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()),
                        doc_id,
                        doc_title,
                        chunk_text,
                        i,
                        json.dumps(embedding) if embedding else None,
                        json.dumps(metadata, ensure_ascii=False),
                        now,
                    ),
                )

        # ドキュメントメタ保存/更新
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rag_documents
                  (doc_id, doc_title, source, chunk_count, content_hash, metadata, indexed_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    doc_id,
                    doc_title,
                    source,
                    len(chunks),
                    content_hash,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                ),
            )

        logger.info(f"[RAGEngine] indexed doc_id={doc_id} chunks={len(chunks)}")
        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        """ドキュメントとそのチャンクを削除する。"""
        with self._conn() as conn:
            conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            result = conn.execute(
                "DELETE FROM rag_documents WHERE doc_id = ?", (doc_id,)
            )
            deleted = result.rowcount > 0
        if deleted:
            logger.info(f"[RAGEngine] deleted doc_id={doc_id}")
        return deleted

    # --------------------------------
    # 検索
    # --------------------------------

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        doc_id_filter: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        クエリに類似するチャンクを取得する。

        Args:
            query: 検索クエリ
            top_k: 取得件数
            doc_id_filter: ドキュメントIDで絞り込む（Noneで全ドキュメント）
            min_score: 最低スコア閾値

        Returns:
            SearchResult のリスト（スコア降順）
        """
        query_embedding = self._get_embedding(query)

        if query_embedding is not None:
            return self._semantic_search(query, query_embedding, top_k, doc_id_filter, min_score)
        else:
            # エンベディング不可の場合はキーワード検索にフォールバック
            logger.warning("[RAGEngine] embedding unavailable, falling back to keyword search")
            return self._keyword_search(query, top_k, doc_id_filter)

    def _semantic_search(
        self,
        query: str,
        query_emb: List[float],
        top_k: int,
        doc_id_filter: Optional[str],
        min_score: float,
    ) -> List[SearchResult]:
        """コサイン類似度でセマンティック検索。"""
        conditions = "embedding IS NOT NULL"
        params: list = []
        if doc_id_filter:
            conditions += " AND doc_id = ?"
            params.append(doc_id_filter)

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM rag_chunks WHERE {conditions}", params
            ).fetchall()

        scored: List[Tuple[float, sqlite3.Row]] = []
        for row in rows:
            try:
                emb = json.loads(row["embedding"])
                score = self._cosine_similarity(query_emb, emb)
                if score >= min_score:
                    scored.append((score, row))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchResult(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                doc_title=row["doc_title"],
                content=row["content"],
                score=score,
                chunk_index=row["chunk_index"],
                metadata=json.loads(row["metadata"]),
            )
            for score, row in scored[:top_k]
        ]

    def _keyword_search(
        self,
        query: str,
        top_k: int,
        doc_id_filter: Optional[str],
    ) -> List[SearchResult]:
        """LIKE によるキーワード検索（フォールバック）。"""
        words = [w for w in query.split() if len(w) > 1]
        if not words:
            return []

        conditions = " AND ".join(["content LIKE ?" for _ in words])
        params: list = [f"%{w}%" for w in words]
        if doc_id_filter:
            conditions += " AND doc_id = ?"
            params.append(doc_id_filter)
        params.append(top_k)

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM rag_chunks WHERE {conditions} LIMIT ?", params
            ).fetchall()

        return [
            SearchResult(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                doc_title=row["doc_title"],
                content=row["content"],
                score=0.5,
                chunk_index=row["chunk_index"],
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    # --------------------------------
    # 生成（RAG pipeline）
    # --------------------------------

    def generate(
        self,
        query: str,
        context_results: Optional[List[SearchResult]] = None,
        top_k: int = DEFAULT_TOP_K,
        llm_model: str = "qwen2.5:7b",
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        クエリと検索結果からLLM回答を生成する（RAGパイプライン）。

        Args:
            query: 質問
            context_results: 事前に取得した検索結果（Noneで自動検索）
            top_k: 自動検索時のチャンク数
            llm_model: 使用するOllamaモデル
            system_prompt: システムプロンプト（カスタマイズ用）
            max_tokens: 最大トークン数

        Returns:
            {"answer": str, "sources": [...], "query": str}
        """
        if context_results is None:
            context_results = self.search(query, top_k=top_k)

        context_text = "\n\n".join(
            f"[出典: {r.doc_title} chunk#{r.chunk_index}]\n{r.content}"
            for r in context_results
        )

        default_system = (
            "あなたは提供されたコンテキストに基づいて質問に答えるアシスタントです。"
            "コンテキストに載っていない情報は「情報なし」とだけ答えてください。"
        )
        prompt = (
            f"コンテキスト:\n{context_text}\n\n"
            f"質問: {query}\n\n回答:"
        )

        answer = self._llm_generate(
            system=system_prompt or default_system,
            prompt=prompt,
            model=llm_model,
            max_tokens=max_tokens,
        )

        return {
            "answer": answer,
            "query": query,
            "sources": [r.to_dict() for r in context_results],
            "model": llm_model,
        }

    def _llm_generate(
        self,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int,
    ) -> str:
        """Ollama /api/generate を呼び出す。"""
        if not HTTPX_AVAILABLE:
            return "[httpx未インストールのためLLM生成不可]"
        try:
            resp = httpx.post(  # type: ignore[possibly-unbound]
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "system": system,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as exc:
            logger.error(f"[RAGEngine] LLM generate error: {exc}")
            return f"[LLM生成エラー: {exc}]"

    # --------------------------------
    # ドキュメント管理
    # --------------------------------

    def list_documents(self) -> List[Dict[str, Any]]:
        """インデックス済みドキュメントの一覧を返す。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM rag_documents ORDER BY indexed_at DESC, rowid DESC"
            ).fetchall()
        return [
            {
                "doc_id": row["doc_id"],
                "doc_title": row["doc_title"],
                "source": row["source"],
                "chunk_count": row["chunk_count"],
                "indexed_at": row["indexed_at"],
                "metadata": json.loads(row["metadata"]),
            }
            for row in rows
        ]

    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """指定ドキュメントのチャンク一覧を返す（embedding除く）。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT chunk_id, doc_id, doc_title, content, chunk_index, metadata "
                "FROM rag_chunks WHERE doc_id = ? ORDER BY chunk_index",
                (doc_id,),
            ).fetchall()
        return [
            {
                "chunk_id": row["chunk_id"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
            }
            for row in rows
        ]

    def stats(self) -> Dict[str, Any]:
        """統計情報を返す。"""
        with self._conn() as conn:
            doc_count = conn.execute("SELECT COUNT(*) FROM rag_documents").fetchone()[0]
            chunk_count = conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0]
            embedded_count = conn.execute(
                "SELECT COUNT(*) FROM rag_chunks WHERE embedding IS NOT NULL"
            ).fetchone()[0]
        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "embedded_chunks": embedded_count,
            "unembedded_chunks": chunk_count - embedded_count,
            "embed_model": self.embed_model,
            "db_path": str(self.db_path),
        }

    # --------------------------------
    # エンベディング
    # --------------------------------

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Ollama でテキストをベクトル化する。
        API が使えない場合は None を返す（キーワード検索にフォールバック）。
        """
        if not HTTPX_AVAILABLE:
            return None

        if self._embed_available is False:
            return None  # 既に失敗済みと判っている

        clean = text.replace("\n", " ").strip()[:2000]
        try:
            resp = httpx.post(  # type: ignore[possibly-unbound]
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": clean},
                timeout=EMBED_TIMEOUT,
            )
            resp.raise_for_status()
            emb = resp.json().get("embedding")
            if emb:
                self._embed_available = True
                return emb
        except Exception as exc:
            if self._embed_available is None:
                logger.warning(f"[RAGEngine] embedding unavailable ({self.embed_model}): {exc}")
                self._embed_available = False
        return None

    # --------------------------------
    # テキスト分割
    # --------------------------------

    def _split_text(self, text: str) -> List[str]:
        """
        テキストをオーバーラップ付きチャンクに分割する。
        段落境界（空行）を優先し、なければ文字数で分割する。
        """
        chunks: List[str] = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current = ""
        for para in paragraphs:
            candidate = (current + "\n\n" + para).strip() if current else para
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # 段落自体がchunk_sizeを超える場合は文字数で分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_by_chars(para)
                    chunks.extend(sub_chunks[:-1])
                    current = sub_chunks[-1] if sub_chunks else ""
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks if chunks else [text[:self.chunk_size]]

    def _split_by_chars(self, text: str) -> List[str]:
        """文字数ベースのオーバーラップ分割。"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks

    # --------------------------------
    # ベクトル演算
    # --------------------------------

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """コサイン類似度を計算する。"""
        if NUMPY_AVAILABLE:
            a = np.array(v1, dtype=np.float32)  # type: ignore[possibly-unbound]
            b = np.array(v2, dtype=np.float32)  # type: ignore[possibly-unbound]
            norm_a = np.linalg.norm(a)  # type: ignore[possibly-unbound]
            norm_b = np.linalg.norm(b)  # type: ignore[possibly-unbound]
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))  # type: ignore[possibly-unbound]
        # numpy なし : 純 Python
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# --------------------------------
# モジュールレベルシングルトン
# --------------------------------

_default_instance: Optional[RAGEngine] = None


def get_rag_engine(db_path: Optional[str] = None) -> RAGEngine:
    """デフォルトの RAGEngine インスタンスを取得（シングルトン）。"""
    global _default_instance
    if _default_instance is None:
        _default_instance = RAGEngine(db_path=db_path)
    return _default_instance
