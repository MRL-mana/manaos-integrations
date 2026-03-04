#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearXNG統合のテストスクリプト
"""

import sys
import os
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from searxng_integration import SearXNGIntegration
import json

try:
    from manaos_integrations._paths import SEARXNG_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import SEARXNG_PORT  # type: ignore
    except Exception:  # pragma: no cover
        SEARXNG_PORT = int(os.getenv("SEARXNG_PORT", "8080"))


def test_searxng_connection():
    """SearXNGへの接続テスト"""
    print("=" * 60)
    print("SearXNG接続テスト")
    print("=" * 60)
    
    searxng = SearXNGIntegration()
    
    # 利用可能性チェック
    if not searxng.is_available():
        print("❌ SearXNGが利用できません")
        print("   確認事項:")
        print("   1. Dockerコンテナが起動しているか: docker ps | grep searxng")
        print(f"   2. http://127.0.0.1:{SEARXNG_PORT} にアクセスできるか")
        print("   3. 環境変数SEARXNG_BASE_URLが正しく設定されているか")
        return False
    
    print("✅ SearXNGに接続できました")
    
    # 状態確認
    status = searxng.get_status()
    print(f"\n📊 状態情報:")
    print(f"   - ベースURL: {status['base_url']}")
    print(f"   - キャッシュ有効: {status['cache']['enabled']}")
    print(f"   - キャッシュファイル数: {status['cache']['cache_files']}")
    print(f"   - キャッシュサイズ: {status['cache']['cache_size_mb']}MB")
    print(f"   - 利用可能な検索エンジン: {status['available_engines']}個")
    
    return True


def test_search():
    """検索機能のテスト"""
    print("\n" + "=" * 60)
    print("検索機能テスト")
    print("=" * 60)
    
    searxng = SearXNGIntegration()
    
    if not searxng.is_available():
        print("❌ SearXNGが利用できません")
        return False
    
    # テスト検索
    query = "Python"
    print(f"\n🔍 検索クエリ: {query}")
    
    result = searxng.search(query, max_results=5)
    
    if result.get("error"):
        print(f"❌ 検索エラー: {result['error']}")
        return False
    
    print(f"✅ 検索成功")
    print(f"   総結果数: {result.get('total_results', 0)}件")
    print(f"   表示件数: {result.get('count', 0)}件")
    
    print("\n📋 検索結果:")
    for i, item in enumerate(result.get("results", [])[:3], 1):
        print(f"\n   {i}. {item.get('title', '')}")
        print(f"      URL: {item.get('url', '')}")
        if item.get('content'):
            content = item.get('content', '')[:100]
            print(f"      概要: {content}...")
    
    return True


def test_search_simple():
    """シンプル検索のテスト"""
    print("\n" + "=" * 60)
    print("シンプル検索テスト")
    print("=" * 60)
    
    searxng = SearXNGIntegration()
    
    if not searxng.is_available():
        print("❌ SearXNGが利用できません")
        return False
    
    query = "Python"
    print(f"\n🔍 検索クエリ: {query}")
    
    results = searxng.search_simple(query, max_results=3)
    
    if not results:
        print("❌ 検索結果がありません")
        return False
    
    print(f"✅ 検索成功 ({len(results)}件)")
    
    print("\n📋 検索結果:")
    for i, item in enumerate(results, 1):
        print(f"   {i}. {item.get('title', '')}")
        print(f"      {item.get('url', '')}")
    
    return True


def test_cache():
    """キャッシュ機能のテスト"""
    print("\n" + "=" * 60)
    print("キャッシュ機能テスト")
    print("=" * 60)
    
    searxng = SearXNGIntegration()
    
    if not searxng.is_available():
        print("❌ SearXNGが利用できません")
        return False
    
    query = "Python"
    
    # 1回目の検索（キャッシュなし）
    print(f"\n🔍 1回目の検索（キャッシュなし）: {query}")
    import time
    start_time = time.time()
    result1 = searxng.search(query, max_results=5)
    elapsed1 = time.time() - start_time
    print(f"   所要時間: {elapsed1:.2f}秒")
    
    # 2回目の検索（キャッシュあり）
    print(f"\n🔍 2回目の検索（キャッシュあり）: {query}")
    start_time = time.time()
    result2 = searxng.search(query, max_results=5)
    elapsed2 = time.time() - start_time
    print(f"   所要時間: {elapsed2:.2f}秒")
    
    if elapsed2 < elapsed1 * 0.5:
        print("✅ キャッシュが機能しています（2回目が高速）")
    else:
        print("⚠️  キャッシュが効いていない可能性があります")
    
    return True


def test_manaos_api():
    """ManaOS標準API経由のテスト"""
    print("\n" + "=" * 60)
    print("ManaOS標準API経由テスト")
    print("=" * 60)
    
    try:
        import manaos_integrations.manaos_core_api as manaos
        
        result = manaos.act("web_search", {
            "query": "Python",
            "max_results": 3
        })
        
        if result.get("error"):
            print(f"❌ エラー: {result['error']}")
            return False
        
        print(f"✅ ManaOS標準API経由で検索成功")
        print(f"   検索結果: {result.get('count', 0)}件")
        
        return True
    
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("SearXNG統合テスト")
    print("=" * 60)
    
    tests = [
        ("接続テスト", test_searxng_connection),
        ("検索機能テスト", test_search),
        ("シンプル検索テスト", test_search_simple),
        ("キャッシュ機能テスト", test_cache),
        ("ManaOS標準API経由テスト", test_manaos_api),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}でエラーが発生しました: {e}")
            results.append((name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{status}: {name}")
    
    success_count = sum(1 for _, result in results if result)
    print(f"\n合計: {success_count}/{len(results)} テスト成功")
    
    return success_count == len(results)



















