"""
人格設定のテスト
"""

import requests
import json
import os

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")

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








