"""
Mem0統合モジュール
AIエージェント向けメモリ管理システムとの統合
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
    print("Mem0ライブラリがインストールされていません。")
    print("インストール: pip install mem0ai")


class Mem0Integration:
    """Mem0統合クラス"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: Mem0設定（オプション）
        """
        self.config = config or {}
        self.memory = None
        
        if MEM0_AVAILABLE:
            self._initialize_memory()
    
    def _initialize_memory(self):
        """メモリシステムを初期化"""
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
                        "base_url": "http://localhost:11434"
                    }
                }
            }
            
            # ユーザー設定で上書き
            config = {**default_config, **self.config}
            
            self.memory = Memory.from_config(config)
            
        except Exception as e:
            print(f"Mem0初期化エラー: {e}")
            # フォールバック: ローカルストレージを使用
            self.memory = None
    
    def is_available(self) -> bool:
        """
        Mem0が利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return MEM0_AVAILABLE and self.memory is not None
    
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
            result = self.memory.add(
                memory_text,
                user_id=user_id or "default",
                metadata=metadata
            )
            return result.get("id") if isinstance(result, dict) else None
            
        except Exception as e:
            print(f"メモリ追加エラー: {e}")
            return None
    
    def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        メモリを検索
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID（オプション）
            limit: 取得数
            
        Returns:
            メモリ情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            results = self.memory.search(
                query,
                user_id=user_id or "default",
                limit=limit
            )
            return results if isinstance(results, list) else []
            
        except Exception as e:
            print(f"メモリ検索エラー: {e}")
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
            memories = self.memory.get_all(user_id=user_id or "default")
            return memories if isinstance(memories, list) else []
            
        except Exception as e:
            print(f"メモリ取得エラー: {e}")
            return []
    
    def update_memory(
        self,
        memory_id: str,
        memory_text: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        メモリを更新
        
        Args:
            memory_id: メモリID
            memory_text: 新しいメモリテキスト
            user_id: ユーザーID（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            self.memory.update(
                memory_id,
                memory_text,
                user_id=user_id or "default"
            )
            return True
            
        except Exception as e:
            print(f"メモリ更新エラー: {e}")
            return False
    
    def delete_memory(
        self,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        メモリを削除
        
        Args:
            memory_id: メモリID
            user_id: ユーザーID（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            self.memory.delete(
                memory_id,
                user_id=user_id or "default"
            )
            return True
            
        except Exception as e:
            print(f"メモリ削除エラー: {e}")
            return False
    
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        メモリ統計を取得
        
        Args:
            user_id: ユーザーID（オプション）
            
        Returns:
            統計情報の辞書
        """
        memories = self.get_all_memories(user_id)
        
        return {
            "total_memories": len(memories),
            "user_id": user_id or "default",
            "last_updated": datetime.now().isoformat()
        }


class SimpleMemoryStore:
    """Mem0が利用できない場合のシンプルなメモリストア"""
    
    def __init__(self, storage_path: str = "./manaos_memories.json"):
        """
        初期化
        
        Args:
            storage_path: ストレージファイルのパス
        """
        self.storage_path = Path(storage_path)
        self.memories = {}
        self._load()
    
    def _load(self):
        """メモリを読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except:
                self.memories = {}
        else:
            self.memories = {}
    
    def _save(self):
        """メモリを保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"メモリ保存エラー: {e}")
    
    def add(self, memory_text: str, user_id: str = "default", metadata: Optional[Dict] = None) -> str:
        """メモリを追加"""
        memory_id = f"mem_{len(self.memories) + 1}_{datetime.now().timestamp()}"
        
        if user_id not in self.memories:
            self.memories[user_id] = []
        
        self.memories[user_id].append({
            "id": memory_id,
            "text": memory_text,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        })
        
        self._save()
        return memory_id
    
    def search(self, query: str, user_id: str = "default", limit: int = 5) -> List[Dict]:
        """メモリを検索"""
        if user_id not in self.memories:
            return []
        
        # シンプルなテキストマッチング
        results = []
        query_lower = query.lower()
        
        for memory in self.memories[user_id]:
            if query_lower in memory["text"].lower():
                results.append(memory)
        
        return results[:limit]
    
    def get_all(self, user_id: str = "default") -> List[Dict]:
        """すべてのメモリを取得"""
        return self.memories.get(user_id, [])


def main():
    """テスト用メイン関数"""
    print("Mem0統合テスト")
    print("=" * 50)
    
    if not MEM0_AVAILABLE:
        print("Mem0がインストールされていません。")
        print("シンプルなメモリストアを使用します。")
        
        store = SimpleMemoryStore()
        memory_id = store.add("これはテストメモリです。", "test_user")
        print(f"メモリ追加: {memory_id}")
        
        results = store.search("テスト", "test_user")
        print(f"検索結果: {len(results)}件")
        return
    
    mem0 = Mem0Integration()
    
    if mem0.is_available():
        print("Mem0が利用可能です。")
        
        # メモリ追加テスト
        memory_id = mem0.add_memory("ManaOSは素晴らしいシステムです。", "mana")
        print(f"メモリ追加: {memory_id}")
        
        # メモリ検索テスト
        results = mem0.search_memories("ManaOS", "mana")
        print(f"検索結果: {len(results)}件")
        
        # 統計取得
        stats = mem0.get_stats("mana")
        print(f"統計: {stats}")
    else:
        print("Mem0が利用できません。")


if __name__ == "__main__":
    main()





















