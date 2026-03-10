"""
Mem0統合モジュール（改善版）
AIエージェント向けメモリ管理システムとの統合
ベースクラスを使用して統一モジュールを活用
"""

import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration


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
        return MEM0_AVAILABLE and self.memory is not None
    
    def _initialize_memory(self) -> bool:
        """
        メモリシステムを初期化
        
        Returns:
            初期化成功かどうか
        """
        try:
            # デフォルト設定
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
                        "model": "qwen2.5:7b",
                        "base_url": "http://127.0.0.1:11434"
                    }
                }
            }
            
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
            # フォールバック: ローカルストレージを使用
            self.memory = None
            return False
    
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






















