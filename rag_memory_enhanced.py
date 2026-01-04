#!/usr/bin/env python3
"""
🧠 RAG記憶進化システム
重要度スコア・重複チェック・時系列メモリ
"""

import os
import json
import httpx
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("RAGMemory")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("RAGMemory")


@dataclass
class MemoryEntry:
    """記憶エントリ"""
    entry_id: str
    content: str
    importance_score: float  # 0.0-1.0
    content_hash: str  # 重複チェック用
    created_at: str
    updated_at: str
    access_count: int
    last_accessed_at: str
    related_entries: List[str]  # 関連エントリID
    temporal_context: Dict[str, Any]  # 時系列コンテキスト
    metadata: Dict[str, Any]


class RAGMemoryEnhanced:
    """RAG記憶進化システム"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースパス
            model: 重要度判定用のモデル
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url
        self.model = model
        self.config_path = config_path or Path(__file__).parent / "rag_memory_config.json"
        self.config = self._load_config()
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "rag_memory.db"
        self._init_database()
        
        # 重複チェック用のハッシュマップ
        self.content_hash_map: Dict[str, str] = {}
        self._load_content_hashes()
        
        logger.info(f"✅ RAG記憶進化システム初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": ["model"],
                    "fields": {
                        "ollama_url": {"type": str, "default": "http://localhost:11434"},
                        "model": {"type": str},
                        "importance_threshold": {"type": (int, float), "default": 0.6},
                        "duplicate_threshold": {"type": (int, float), "default": 0.9},
                        "temporal_window_days": {"type": int, "default": 30},
                        "max_entries": {"type": int, "default": 10000}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": "http://localhost:11434",
            "model": "qwen2.5:14b",
            "importance_threshold": 0.6,
            "duplicate_threshold": 0.9,
            "temporal_window_days": 30,
            "max_entries": 10000
        }
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # メモリエントリテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                importance_score REAL NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                related_entries TEXT,
                temporal_context TEXT,
                metadata TEXT
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON memory_entries(content_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memory_entries(created_at DESC)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def _load_content_hashes(self):
        """コンテンツハッシュを読み込む"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT entry_id, content_hash FROM memory_entries")
        for row in cursor.fetchall():
            entry_id, content_hash = row
            self.content_hash_map[content_hash] = entry_id
        
        conn.close()
        logger.info(f"✅ コンテンツハッシュ読み込み完了: {len(self.content_hash_map)}件")
    
    def _calculate_content_hash(self, content: str) -> str:
        """コンテンツハッシュを計算"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_importance_score(self, content: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        重要度スコアを計算
        
        Args:
            content: コンテンツ
            context: コンテキスト情報
        
        Returns:
            float: 重要度スコア (0.0-1.0)
        """
        # ルールベースの重要度判定
        importance_keywords = [
            "重要", "必須", "必要", "緊急", "優先",
            "完了", "成功", "失敗", "エラー",
            "設定", "変更", "更新", "削除"
        ]
        
        content_lower = content.lower()
        keyword_count = sum(1 for keyword in importance_keywords if keyword in content_lower)
        
        # キーワードベースのスコア
        keyword_score = min(0.7, 0.3 + keyword_count * 0.1)
        
        # LLMベースの重要度判定（オプション）
        try:
            prompt = f"""以下の情報の重要度を0.0-1.0で評価してください。

情報: {content[:500]}

重要度の基準:
- 0.9-1.0: 非常に重要（設定変更、重要な決定、エラー情報など）
- 0.7-0.9: 重要（完了報告、進捗情報など）
- 0.5-0.7: やや重要（一般的な情報）
- 0.3-0.5: 低重要度（雑談、一時的な情報）
- 0.0-0.3: 重要でない（不要な情報）

重要度スコア（0.0-1.0の数値のみ）:"""
            
            timeout = timeout_config.get("llm_call", 30.0)
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 50
                    }
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                # 数値を抽出
                try:
                    llm_score = float(result_text.split()[0])
                    llm_score = max(0.0, min(1.0, llm_score))
                    # キーワードスコアとLLMスコアの平均
                    final_score = (keyword_score + llm_score) / 2
                    return final_score
                except (ValueError, IndexError):
                    pass
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                user_message="重要度判定に失敗しました"
            )
            logger.warning(f"LLM重要度判定エラー: {error.message}")
        
        return keyword_score
    
    def _check_duplicate(self, content: str) -> Optional[str]:
        """
        重複チェック
        
        Args:
            content: チェックするコンテンツ
        
        Returns:
            Optional[str]: 重複エントリID（重複がない場合はNone）
        """
        content_hash = self._calculate_content_hash(content)
        
        # ハッシュマップで高速チェック
        if content_hash in self.content_hash_map:
            return self.content_hash_map[content_hash]
        
        # 類似度チェック（オプション）
        # ここでは簡易的にハッシュのみでチェック
        # より高度な類似度チェックが必要な場合は、ベクトル類似度を使用
        
        return None
    
    def _merge_entries(self, existing_id: str, new_content: str, new_metadata: Dict[str, Any]):
        """重複エントリを統合"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 既存エントリを取得
        cursor.execute("SELECT * FROM memory_entries WHERE entry_id = ?", (existing_id,))
        row = cursor.fetchone()
        
        if row:
            # メタデータを更新
            existing_metadata = json.loads(row[10]) if row[10] else {}
            existing_metadata.update(new_metadata)
            
            # アクセス回数を増やす
            access_count = row[6] + 1
            
            # 更新
            cursor.execute("""
                UPDATE memory_entries
                SET updated_at = ?,
                    access_count = ?,
                    last_accessed_at = ?,
                    metadata = ?
                WHERE entry_id = ?
            """, (
                datetime.now().isoformat(),
                access_count,
                datetime.now().isoformat(),
                json.dumps(existing_metadata, ensure_ascii=False),
                existing_id
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ エントリ統合完了: {existing_id}")
    
    def _get_temporal_context(self, content: str) -> Dict[str, Any]:
        """時系列コンテキストを取得"""
        # 関連する過去のエントリを検索
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近のエントリを取得
        window_days = self.config.get("temporal_window_days", 30)
        cutoff_date = (datetime.now() - timedelta(days=window_days)).isoformat()
        
        cursor.execute("""
            SELECT entry_id, content, created_at
            FROM memory_entries
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (cutoff_date,))
        
        recent_entries = []
        for row in cursor.fetchall():
            recent_entries.append({
                "entry_id": row[0],
                "content": row[1][:200],  # 最初の200文字
                "created_at": row[2]
            })
        
        conn.close()
        
        return {
            "recent_entries": recent_entries,
            "window_days": window_days
        }
    
    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        force_importance: Optional[float] = None
    ) -> MemoryEntry:
        """
        記憶を追加
        
        Args:
            content: 記憶するコンテンツ
            metadata: メタデータ
            force_importance: 強制的な重要度スコア
        
        Returns:
            MemoryEntry: 記憶エントリ
        """
        # 重複チェック
        duplicate_id = self._check_duplicate(content)
        if duplicate_id:
            logger.info(f"⚠️ 重複エントリ検出: {duplicate_id}")
            self._merge_entries(duplicate_id, content, metadata or {})
            # 統合後のエントリを返す
            return self.get_memory(duplicate_id)
        
        # 重要度スコアを計算
        if force_importance is not None:
            importance_score = force_importance
        else:
            importance_score = self._calculate_importance_score(content, metadata)
        
        # 重要度が閾値以下の場合は保存しない
        threshold = self.config.get("importance_threshold", 0.6)
        if importance_score < threshold:
            logger.info(f"⚠️ 重要度が低いため保存をスキップ: {importance_score:.2f} < {threshold}")
            # 一時的なエントリとして作成（保存はしない）
            entry_id = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return MemoryEntry(
                entry_id=entry_id,
                content=content,
                importance_score=importance_score,
                content_hash=self._calculate_content_hash(content),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                access_count=0,
                last_accessed_at=datetime.now().isoformat(),
                related_entries=[],
                temporal_context={},
                metadata=metadata or {}
            )
        
        # 時系列コンテキストを取得
        temporal_context = self._get_temporal_context(content)
        
        # エントリIDを生成
        entry_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000}"
        
        # データベースに保存
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memory_entries (
                entry_id, content, importance_score, content_hash,
                created_at, updated_at, access_count, last_accessed_at,
                related_entries, temporal_context, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            content,
            importance_score,
            self._calculate_content_hash(content),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            0,
            datetime.now().isoformat(),
            json.dumps([], ensure_ascii=False),
            json.dumps(temporal_context, ensure_ascii=False),
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        # ハッシュマップを更新
        self.content_hash_map[self._calculate_content_hash(content)] = entry_id
        
        logger.info(f"✅ 記憶追加完了: {entry_id} (重要度: {importance_score:.2f})")
        
        return MemoryEntry(
            entry_id=entry_id,
            content=content,
            importance_score=importance_score,
            content_hash=self._calculate_content_hash(content),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            access_count=0,
            last_accessed_at=datetime.now().isoformat(),
            related_entries=[],
            temporal_context=temporal_context,
            metadata=metadata or {}
        )
    
    def get_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """記憶を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM memory_entries WHERE entry_id = ?", (entry_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # アクセス情報を更新
        cursor.execute("""
            UPDATE memory_entries
            SET access_count = access_count + 1,
                last_accessed_at = ?
            WHERE entry_id = ?
        """, (datetime.now().isoformat(), entry_id))
        
        conn.commit()
        conn.close()
        
        return MemoryEntry(
            entry_id=row[0],
            content=row[1],
            importance_score=row[2],
            content_hash=row[3],
            created_at=row[4],
            updated_at=row[5],
            access_count=row[6],
            last_accessed_at=row[7],
            related_entries=json.loads(row[8]) if row[8] else [],
            temporal_context=json.loads(row[9]) if row[9] else {},
            metadata=json.loads(row[10]) if row[10] else {}
        )
    
    def search_memories(
        self,
        query: str,
        min_importance: float = 0.0,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """記憶を検索"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 重要度とクエリで検索
        cursor.execute("""
            SELECT * FROM memory_entries
            WHERE importance_score >= ?
            AND content LIKE ?
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ?
        """, (min_importance, f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            memories.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                importance_score=row[2],
                content_hash=row[3],
                created_at=row[4],
                updated_at=row[5],
                access_count=row[6],
                last_accessed_at=row[7],
                related_entries=json.loads(row[8]) if row[8] else [],
                temporal_context=json.loads(row[9]) if row[9] else {},
                metadata=json.loads(row[10]) if row[10] else {}
            ))
        
        return memories
    
    def get_important_memories(self, limit: int = 20) -> List[MemoryEntry]:
        """重要な記憶を取得"""
        return self.search_memories("", min_importance=0.7, limit=limit)
    
    def get_temporal_memories(self, days: int = 7) -> List[MemoryEntry]:
        """時系列記憶を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM memory_entries
            WHERE created_at >= ?
            ORDER BY created_at DESC
        """, (cutoff_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            memories.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                importance_score=row[2],
                content_hash=row[3],
                created_at=row[4],
                updated_at=row[5],
                access_count=row[6],
                last_accessed_at=row[7],
                related_entries=json.loads(row[8]) if row[8] else [],
                temporal_context=json.loads(row[9]) if row[9] else {},
                metadata=json.loads(row[10]) if row[10] else {}
            ))
        
        return memories


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルメモリインスタンス
memory = None

def init_memory():
    """メモリを初期化"""
    global memory
    if memory is None:
        memory = RAGMemoryEnhanced()
    return memory

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "RAG Memory Enhanced"})

@app.route('/api/add', methods=['POST'])
def add_memory_endpoint():
    """記憶追加エンドポイント"""
    try:
        data = request.get_json() or {}
        content = data.get("content", "")
        
        if not content:
            error = error_handler.handle_exception(
                ValueError("content is required"),
                context={"endpoint": "/api/add"},
                user_message="記憶内容が必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        memory = init_memory()
        entry = memory.add_memory(
            content=content,
            metadata=data.get("metadata"),
            force_importance=data.get("importance_score")
        )
        
        return jsonify(asdict(entry))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/add"},
            user_message="記憶追加エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/get/<entry_id>', methods=['GET'])
def get_memory_endpoint(entry_id: str):
    """記憶取得エンドポイント"""
    try:
        memory = init_memory()
        entry = memory.get_memory(entry_id)
        
        if not entry:
            error = error_handler.handle_exception(
                FileNotFoundError(f"Memory not found: {entry_id}"),
                context={"endpoint": "/api/get/<entry_id>", "entry_id": entry_id},
                user_message="記憶が見つかりません"
            )
            return jsonify(error.to_json_response()), 404
        
        return jsonify(asdict(entry))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/get/<entry_id>", "entry_id": entry_id},
            user_message="記憶取得エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/search', methods=['POST'])
def search_memories_endpoint():
    """記憶検索エンドポイント"""
    try:
        data = request.get_json() or {}
        query = data.get("query", "")
        min_importance = data.get("min_importance", 0.0)
        limit = data.get("limit", 10)
        
        memory = init_memory()
        memories = memory.search_memories(query, min_importance, limit)
        
        return jsonify({
            "results": [asdict(m) for m in memories],
            "count": len(memories)
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/search"},
            user_message="記憶検索エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/important', methods=['GET'])
def get_important_memories_endpoint():
    """重要な記憶取得エンドポイント"""
    limit = request.args.get("limit", 20, type=int)
    
    memory = init_memory()
    memories = memory.get_important_memories(limit)
    
    return jsonify({
        "results": [asdict(m) for m in memories],
        "count": len(memories)
    })

@app.route('/api/temporal', methods=['GET'])
def get_temporal_memories_endpoint():
    """時系列記憶取得エンドポイント"""
    days = request.args.get("days", 7, type=int)
    
    memory = init_memory()
    memories = memory.get_temporal_memories(days)
    
    return jsonify({
        "results": [asdict(m) for m in memories],
        "count": len(memories)
    })


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5103))
    logger.info(f"🧠 RAG記憶進化システム起動中... (ポート: {port})")
    init_memory()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

