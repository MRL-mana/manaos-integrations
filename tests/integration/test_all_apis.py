#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
追加したAPI統合の動作確認テスト
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
    
    try:
        from brave_search_integration import BraveSearchIntegration
        
        brave = BraveSearchIntegration()
        
        if not brave.is_available():
            print("[NG] Brave Search APIキーが設定されていません")
            return False
        
        print("[OK] Brave Search APIキーが設定されています")
        print(f"   APIキー: {brave.api_key[:10]}...")
        print()
        
        print("[INFO] テスト検索を実行中...")
        results = brave.search_simple(query="Python programming", count=3)
        
        if results:
            print(f"[OK] {len(results)}件の結果を取得しました")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['title']}")
                print(f"      {result['url']}")
            return True
        else:
            print("[WARN] 検索結果がありませんでした（APIキーが無効の可能性があります）")
            return False
            
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def test_base_ai():
    """Base AI APIのテスト"""
    print()
    print("=" * 70)
    print("Base AI API テスト")
    print("=" * 70)
    
    try:
        from base_ai_integration import BaseAIIntegration
        
        # 通常のAPIキーをテスト
        base_ai = BaseAIIntegration(use_free=False)
        
        if not base_ai.is_available():
            print("[NG] Base AI APIキーが設定されていません")
            return False
        
        print("[OK] Base AI APIキーが設定されています")
        print(f"   APIキー: {base_ai.api_key[:10]}...")
        print()
        
        # 無料のAI APIキーをテスト
        base_ai_free = BaseAIIntegration(use_free=True)
        
        if base_ai_free.is_available():
            print("[OK] Base AI 無料のAI APIキーも設定されています")
            print(f"   APIキー: {base_ai_free.api_key[:10]}...")
        else:
            print("[WARN] Base AI 無料のAI APIキーが設定されていません")
        
        print()
        print("[INFO] Base AI APIは実際のAPIリクエストでテストしてください")
        print("   （APIキーが有効かどうかは実際のリクエストで確認できます）")
        
        return True
            
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
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
    print("テスト結果")
    print("=" * 70)
    
    for api_name, success in results.items():
        status = "[OK]" if success else "[NG]"
        print(f"{api_name}: {status}")
    
    print()
    print("=" * 70)
    print("次のステップ")
    print("=" * 70)
    print()
    print("1. CursorからMCPツールを使用:")
    print("   - brave_search(query=\"Python\")")
    print("   - base_ai_chat(prompt=\"こんにちは\")")
    print()
    print("2. 実際のAPIリクエストで動作確認")
    print("3. エラーが出る場合は、APIキーが有効か確認してください")
    print()

