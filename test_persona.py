"""
人格設定のテスト
"""

import requests
import json

API_BASE = "http://localhost:9500"

def test_persona_chat():
    """人格設定が適用されたチャットをテスト"""
    print("=" * 60)
    print("人格設定テスト")
    print("=" * 60)
    
    # チャットリクエスト
    data = {
        "messages": [
            {
                "role": "user",
                "content": "こんにちは！あなたは誰ですか？"
            }
        ],
        "model": "qwen2.5:7b",
        "task_type": "conversation"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/llm/chat",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n[成功] チャット応答:")
            print(f"  応答: {result.get('response', '')[:200]}...")
            print(f"  モデル: {result.get('model', 'unknown')}")
            print(f"  レイテンシ: {result.get('latency_ms', 0)}ms")
        else:
            print(f"\n[エラー] HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"\n[エラー] {e}")


if __name__ == "__main__":
    test_persona_chat()



