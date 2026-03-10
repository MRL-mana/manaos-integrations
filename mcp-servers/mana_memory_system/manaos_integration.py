#!/usr/bin/env python3
"""
ManaOS統合アダプター
新しい三層構造記憶システムをManaOSに統合

統合ポイント:
1. memory_trinity_integration.py の置き換え
2. memory_system_service.py との統合
3. unified_api_gateway.py へのエンドポイント追加
"""

import sys
from pathlib import Path

# 新しい記憶システムをインポート
sys.path.insert(0, str(Path(__file__).parent))
from hot_memory_api import get_api as get_hot_memory_api
from unified_search_api import UnifiedSearchAPI

import logging
logger = logging.getLogger(__name__)


class ManaOSMemoryAdapter:
    """ManaOS統合用アダプター"""

    def __init__(self):
        self.hot_api = get_hot_memory_api()
        self.search_api = UnifiedSearchAPI()
        logger.info("ManaOS Memory Adapter 初期化完了")

    def save_memory(self, content: str, importance: int = 5,
                    category: str = None, source: str = None,  # type: ignore
                    metadata: dict = None) -> dict:  # type: ignore
        """記憶を保存（ManaOS互換）"""
        try:
            success = self.hot_api.save_memory(
                content=content,
                importance=importance,
                category=category,
                source=source or "manaos",
                metadata=metadata,
                auto_sync=True  # Obsidian自動同期
            )

            return {
                "success": success,
                "message": "記憶を保存しました" if success else "保存に失敗しました"
            }
        except Exception as e:
            logger.error(f"記憶保存エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def search_memory(self, query: str, limit: int = 10) -> dict:
        """記憶を検索（ManaOS互換）"""
        try:
            results = self.search_api.search(query, limit=limit)

            # ManaOS互換形式に変換
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "importance": result.get("importance", 5),
                    "category": result.get("category"),
                    "source": result.get("source"),
                    "layer": result.get("layer"),
                    "created_at": result.get("created_at"),
                    "type": result.get("type")
                })

            return {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            logger.error(f"記憶検索エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def get_memories_by_category(self, category: str, limit: int = 20) -> dict:
        """カテゴリで記憶を取得"""
        try:
            results = self.search_api.search_by_category(category, limit)

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "importance": result.get("importance", 5),
                    "category": result.get("category"),
                    "created_at": result.get("created_at")
                })

            return {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            logger.error(f"カテゴリ検索エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def get_important_memories(self, min_importance: int = 7, limit: int = 20) -> dict:
        """重要度の高い記憶を取得"""
        try:
            results = self.search_api.search_by_importance(min_importance, limit)

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "importance": result.get("importance", 5),
                    "category": result.get("category"),
                    "created_at": result.get("created_at")
                })

            return {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            logger.error(f"重要度検索エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def get_stats(self) -> dict:
        """統計情報を取得"""
        try:
            stats = self.search_api.get_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# グローバルインスタンス
_adapter_instance = None

def get_manaos_memory_adapter() -> ManaOSMemoryAdapter:
    """ManaOS Memory Adapterインスタンスを取得"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ManaOSMemoryAdapter()
    return _adapter_instance


if __name__ == '__main__':
    # テスト実行
    adapter = get_manaos_memory_adapter()

    # テスト保存
    result = adapter.save_memory("ManaOS統合テスト", importance=7, category="test")
    print(f"保存結果: {result}")

    # テスト検索
    result = adapter.search_memory("テスト", limit=5)
    print(f"検索結果: {result['count']}件")

    # 統計
    stats = adapter.get_stats()
    print(f"統計: {stats}")








