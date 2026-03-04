#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brave Search API統合のテストスクリプト
"""

import os
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from brave_search_integration import BraveSearchIntegration

def test_brave_search():
    """Brave Search APIのテスト"""
    print("=" * 70)
    print("Brave Search API統合テスト")
    print("=" * 70)
    print()
    
    # APIキーの確認
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        print("[ERROR] BRAVE_API_KEYが設定されていません")
        print("環境変数を設定するか、.envファイルに追加してください")
        return False
    
    print(f"[OK] APIキーが設定されています: {api_key[:10]}...")
    print()
    
    # Brave Search統合を初期化
    brave = BraveSearchIntegration()
    
    if not brave.is_available():
        print("[ERROR] Brave Search APIが利用できません")
        return False
    
    print("[OK] Brave Search統合を初期化しました")
    print()
    
    # テスト検索
    print("[1] テスト検索を実行中...")
    print("-" * 70)
    
    test_query = "Python programming"
    print(f"検索クエリ: {test_query}")
    
    results = brave.search(query=test_query, count=5)
    
    if not results:
        print("[WARN] 検索結果がありませんでした")
        return False
    
    print(f"[OK] {len(results)}件の結果を取得しました")
    print()
    
    # 結果を表示
    print("[2] 検索結果:")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   説明: {result.description[:100]}...")
        if result.age:
            print(f"   公開日: {result.age}")
        print()
    
    # シンプル検索のテスト
    print("[3] シンプル検索のテスト...")
    print("-" * 70)
    
    simple_results = brave.search_simple(query="Python", count=3)
    
    if simple_results:
        print(f"[OK] {len(simple_results)}件の結果を取得しました")
        for i, result in enumerate(simple_results, 1):
            print(f"{i}. {result['title']}")
            print(f"   {result['url']}")
    else:
        print("[WARN] シンプル検索の結果がありませんでした")
    
    print()
    
    # サマリー検索のテスト
    print("[4] サマリー検索のテスト...")
    print("-" * 70)
    
    summary = brave.search_with_summary(query="Python", count=3)
    
    if summary:
        print(f"[OK] サマリーを取得しました")
        print(f"クエリ: {summary['query']}")
        print(f"総結果数: {summary['total_results']}件")
        print(f"結果数: {len(summary['results'])}件")
    else:
        print("[WARN] サマリー検索の結果がありませんでした")
    
    print()
    print("=" * 70)
    print("テスト完了")
    print("=" * 70)
    
    return True


