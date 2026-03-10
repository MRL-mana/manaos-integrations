"""
Mem0統合モジュール（改善版）
AIエージェント向けメモリ管理システムとの統合
ベースクラスを使用して統一モジュールを活用
"""

import os
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import uuid

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration
from _paths import OLLAMA_PORT


class Mem0Integration(BaseIntegration):
    """Mem0統合クラス（改善版）"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: Mem0設定（オプション）
        """
        super().__init__("Mem0")
        self.config = config or {}
        self.memory = None
        self._fallback = _LocalMemoryFallback(Path("./mem0_storage/fallback_memories.jsonl"))
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not MEM0_AVAILABLE:
            self.logger.warning("Mem0ライブラリがインストールされていません")
            return False
        
        return self._initialize_memory()
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return self.memory is not None
    
    def _initialize_memory(self) -> bool:
        """
        メモリシステムを初期化
        
        Returns:
            初期化成功かどうか
        """
        try:
            # デフォルト設定
            # OpenAI APIは保留のため、Ollamaを使用（無料、ローカル）
            ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
            ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            
            default_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "manaos_memories",
                        "path": "./mem0_storage"
                    }
                },
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": ollama_model,
                        "base_url": ollama_url  # Mem0の最新バージョンではbase_urlを使用
                    }
                }
            }
            
            self.logger.info(f"Mem0統合: Ollamaを使用（無料） - {ollama_url}/{ollama_model}")
            
            # ユーザー設定で上書き
            config = {**default_config, **self.config}
            
            self.memory = Memory.from_config(config)  # type: ignore[possibly-unbound]
            self.logger.info("Mem0メモリシステムを初期化しました")
            return True
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"config": self.config, "action": "initialize_memory"},
                user_message="Mem0の初期化に失敗しました"
            )
            self.logger.error(f"Mem0初期化エラー: {error.message}")
            self.memory = self._fallback
            self.logger.warning("Mem0互換フォールバックで継続します")
            return True
    
    def add_memory(
        self,
        memory_text: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        メモリを追加
        
        Args:
            memory_text: メモリテキスト
            user_id: ユーザーID（オプション）
            metadata: メタデータ（オプション）
            
        Returns:
            メモリID（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            result = self.memory.add(  # type: ignore[union-attr]
                memory_text,
                user_id=user_id or "default",
                metadata=metadata
            )
            
            memory_id = result.get("memory_id") if isinstance(result, dict) else str(result)
            self.logger.info(f"メモリを追加しました: {memory_id}")
            return memory_id  # type: ignore
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"memory_text": memory_text[:50], "user_id": user_id, "action": "add_memory"},
                user_message="メモリの追加に失敗しました"
            )
            self.logger.error(f"メモリ追加エラー: {error.message}")
            return None
    
    def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        メモリを検索
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID（オプション）
            limit: 最大取得数
            
        Returns:
            メモリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            results = self.memory.search(  # type: ignore[union-attr]
                query,
                user_id=user_id or "default",
                limit=limit
            )
            
            return results if isinstance(results, list) else []
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"query": query, "user_id": user_id, "action": "search_memories"},
                user_message="メモリの検索に失敗しました"
            )
            self.logger.error(f"メモリ検索エラー: {error.message}")
            return []
    
    def get_all_memories(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        すべてのメモリを取得
        
        Args:
            user_id: ユーザーID（オプション）
            
        Returns:
            メモリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            results = self.memory.get_all(user_id=user_id or "default")  # type: ignore[union-attr]
            return results if isinstance(results, list) else []
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"user_id": user_id, "action": "get_all_memories"},
                user_message="メモリの取得に失敗しました"
            )
            self.logger.error(f"メモリ取得エラー: {error.message}")
            return []


class _LocalMemoryFallback:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        records: List[Dict[str, Any]] = []
        with self.storage_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def _append(self, record: Dict[str, Any]) -> None:
        with self.storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def add(self, memory_text: str, user_id: str = "default", metadata: Optional[Dict[str, Any]] = None):
        memory_id = str(uuid.uuid4())
        record = {
            "id": memory_id,
            "memory": memory_text,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        self._append(record)
        return {"memory_id": memory_id}

    def search(self, query: str, user_id: str = "default", limit: int = 10):
        query_terms = [term for term in query.lower().split() if term]
        records = [item for item in self._load() if item.get("user_id") == user_id]

        def score(item: Dict[str, Any]) -> int:
            text = str(item.get("memory", "")).lower()
            return sum(1 for term in query_terms if term in text)

        ranked = sorted(records, key=lambda item: score(item), reverse=True)
        filtered = [item for item in ranked if score(item) > 0] if query_terms else ranked
        return filtered[:limit]

    def get_all(self, user_id: str = "default"):
        return [item for item in self._load() if item.get("user_id") == user_id]

