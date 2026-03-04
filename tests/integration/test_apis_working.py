#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API統合の動作確認テスト
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

def test_brave_search():
    """Brave Search APIのテスト"""
    print("=" * 70)
    print("Brave Search API テスト")
    print("=" * 70)
    print()
    
    try:
        from brave_search_integration import BraveSearchIntegration
        
        brave = BraveSearchIntegration()
        
        if not brave.is_available():
            print("[NG] Brave Search APIキーが設定されていません")
            return False
        
        print("[OK] Brave Search APIキーが設定されています")
        print(f"   APIキー: {brave.api_key[:10]}...")
        print()
        
        print("[INFO] テスト検索を実行中: 'Python programming'...")
        results = brave.search_simple(query="Python programming", count=3)
        
        if results:
            print(f"[OK] {len(results)}件の結果を取得しました！")
            print()
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['title']}")
                print(f"      URL: {result['url']}")
                if result.get('description'):
                    desc = result['description'][:100]
                    print(f"      説明: {desc}...")
                print()
            return True
        else:
            print("[WARN] 検索結果がありませんでした")
            return False
            
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_base_ai():
    """Base AI APIのテスト"""
    print()
    print("=" * 70)
    print("Base AI API テスト")
    print("=" * 70)
    print()
    
    try:
        from base_ai_integration import BaseAIIntegration
        
        # 無料のAI APIキーをテスト
        base_ai = BaseAIIntegration(use_free=True)
        
        if not base_ai.is_available():
            print("[NG] Base AI 無料のAI APIキーが設定されていません")
            return False
        
        print("[OK] Base AI 無料のAI APIキーが設定されています")
        print(f"   APIキー: {base_ai.api_key[:10]}...")
        print()
        
        print("[INFO] テストチャットを実行中: 'こんにちは！自己紹介してください'...")
        response = base_ai.chat_simple(
            prompt="こんにちは！自己紹介してください",
            system_prompt="あなたは親切なAIアシスタントです。"
        )
        
        if response:
            print("[OK] レスポンスを取得しました！")
            print()
            print("レスポンス:")
            print("-" * 70)
            print(response)
            print("-" * 70)
            return True
        else:
            print("[WARN] レスポンスが空でした")
            return False
            
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン処理"""
    print()
    print("=" * 70)
    print("API統合 動作確認テスト")
    print("=" * 70)
    print()
    
    results = {
        "Brave Search": test_brave_search(),
        "Base AI": test_base_ai()
    }
    
    print()
    print("=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)
    
    for api_name, success in results.items():
        status = "[OK] 動作確認済み" if success else "[NG] エラーあり"
        print(f"{api_name}: {status}")
    
    print()
    print("=" * 70)
    
    if all(results.values()):
        print("[SUCCESS] すべてのAPIが正常に動作しています！")
    else:
        print("[WARN] 一部のAPIでエラーが発生しました")
    
    print("=" * 70)
    print()



