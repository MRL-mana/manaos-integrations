"""
OllamaとManaOS記憶システムの統合テスト
"""

import requests
import json
from typing import List, Dict

# APIサーバーのURL
API_URL = "http://localhost:9405"

def test_ollama_chat_with_memory():
    """Ollamaチャットと記憶システムの統合テスト"""
    print("=" * 60)
    print("OllamaとManaOS記憶システムの統合テスト")
    print("=" * 60)
    
    # テスト1: 基本的なチャット
    print("\n[テスト1] 基本的なチャット（自動保存）")
    messages = [
        {"role": "user", "content": "こんにちは、私はマナです。秋田県に住んでいます。"}
    ]
    
    try:
        response = requests.post(
            f"{API_URL}/api/llm/chat",
            json={
                "messages": messages,
                "auto_save": True,
                "load_history": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"  モデル: {result.get('model')}")
            print(f"  レスポンス: {result.get('response', '')[:100]}...")
            print(f"  レイテンシ: {result.get('latency_ms')}ms")
        else:
            print(f"❌ 失敗: HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テスト2: 会話履歴の読み込み
    print("\n[テスト2] 過去の会話履歴を読み込んでチャット")
    messages2 = [
        {"role": "user", "content": "私の名前を覚えていますか？"}
    ]
    
    try:
        response = requests.post(
            f"{API_URL}/api/llm/chat",
            json={
                "messages": messages2,
                "auto_save": True,
                "load_history": True  # 過去の会話を読み込む
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"  レスポンス: {result.get('response', '')[:200]}...")
        else:
            print(f"❌ 失敗: HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テスト3: 記憶システムから検索
    print("\n[テスト3] 記憶システムから検索")
    try:
        response = requests.get(
            f"{API_URL}/api/memory/recall",
            params={
                "query": "マナ",
                "scope": "all",
                "limit": 5
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"  検索結果: {result.get('count')}件")
            for i, item in enumerate(result.get('results', [])[:3], 1):
                content = item.get('content', '')[:100]
                print(f"  {i}. {content}...")
        else:
            print(f"❌ 失敗: HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    test_ollama_chat_with_memory()



