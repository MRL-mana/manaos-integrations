"""
統一記憶システムのテスト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from memory_unified import UnifiedMemory
import manaos_core_api as manaos


def test_memory_unified():
    """統一記憶システムのテスト"""
    print("=" * 60)
    print("統一記憶システム テスト")
    print("=" * 60)
    
    memory = UnifiedMemory()
    
    # 1. 記憶への保存（入口が1個）
    print("\n[1] 記憶への保存（store）")
    print("-" * 60)
    try:
        memory_id = memory.store({
            "content": "今日はいい天気でした。manaOSのテストをしています。",
            "metadata": {"source": "test", "tags": ["test", "memory"]}
        }, format_type="conversation")
        print(f"✅ 保存成功: {memory_id}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 2. 記憶からの検索（出口が1個）
    print("\n[2] 記憶からの検索（recall）")
    print("-" * 60)
    try:
        results = memory.recall("天気", scope="all", limit=5)
        print(f"✅ 検索成功: {len(results)}件")
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. {result.get('content', '')[:50]}...")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 3. 失敗時のローカルキャッシュ退避
    print("\n[3] 失敗時のローカルキャッシュ退避")
    print("-" * 60)
    # Obsidianが利用できない場合のテスト
    if not memory.obsidian:
        print("⚠️  Obsidianが利用できないため、ローカルキャッシュに保存されます")
        try:
            memory_id = memory.store({
                "content": "ローカルキャッシュテスト",
                "metadata": {"source": "cache_test"}
            }, format_type="memo")
            print(f"✅ ローカルキャッシュ保存成功: {memory_id}")
        except Exception as e:
            print(f"❌ エラー: {e}")
    else:
        print("✅ Obsidianが利用可能です")
    
    # 4. スコープ別検索
    print("\n[4] スコープ別検索")
    print("-" * 60)
    for scope in ["all", "today", "week", "month"]:
        try:
            results = memory.recall("test", scope=scope, limit=5)
            print(f"   {scope}: {len(results)}件")
        except Exception as e:
            print(f"   {scope}: エラー - {e}")


def test_manaos_core_api_memory():
    """manaOS標準API経由での記憶テスト"""
    print("\n" + "=" * 60)
    print("manaOS標準API経由 記憶テスト")
    print("=" * 60)
    
    # 1. 記憶への保存
    print("\n[1] 記憶への保存（remember）")
    print("-" * 60)
    try:
        memory_entry = manaos.remember({
            "type": "conversation",
            "content": "manaOS標準API経由のテストです。"
        }, format_type="conversation")
        print(f"✅ 保存成功: {memory_entry['memory_id']}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 2. 記憶からの検索
    print("\n[2] 記憶からの検索（recall）")
    print("-" * 60)
    try:
        results = manaos.recall("テスト", scope="all", limit=5)
        print(f"✅ 検索成功: {len(results)}件")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    # 統一記憶システムのテスト
    test_memory_unified()
    
    # manaOS標準API経由のテスト
    test_manaos_core_api_memory()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


















