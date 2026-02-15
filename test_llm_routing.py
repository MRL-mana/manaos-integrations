"""
LLMルーティングシステムの統合テスト
"""

import requests
import json
import time
from typing import Dict, Any

# APIエンドポイント
BASE_URL = "http://127.0.0.1:9510/api/llm"


def test_health_check():
    """ヘルスチェックテスト"""
    print("=== ヘルスチェック ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        print()
        return False


def test_get_models():
    """モデル一覧取得テスト"""
    print("=== モデル一覧取得 ===")
    try:
        response = requests.get(f"{BASE_URL}/models")
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        print()
        return False


def test_analyze_difficulty(prompt: str, context: Dict[str, Any] = None):
    """難易度分析テスト"""
    print(f"=== 難易度分析: {prompt[:50]}... ===")
    try:
        data = {
            "prompt": prompt,
            "context": context or {}
        }
        response = requests.post(f"{BASE_URL}/analyze", json=data)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        print()
        return False


def test_route_llm(prompt: str, context: Dict[str, Any] = None, preferences: Dict[str, Any] = None):
    """LLMルーティングテスト"""
    print(f"=== LLMルーティング: {prompt[:50]}... ===")
    try:
        data = {
            "prompt": prompt,
            "context": context or {},
            "preferences": preferences or {}
        }
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/route", json=data, timeout=300)
        elapsed_time = time.time() - start_time
        
        print(f"ステータスコード: {response.status_code}")
        result = response.json()
        print(f"選択モデル: {result.get('model')}")
        print(f"難易度スコア: {result.get('difficulty_score', 0):.2f}")
        print(f"難易度レベル: {result.get('difficulty_level')}")
        print(f"理由: {result.get('reasoning')}")
        print(f"レスポンス時間: {result.get('response_time_ms', 0)}ms")
        print(f"実際の経過時間: {elapsed_time:.2f}秒")
        if result.get('response'):
            print(f"応答（最初の100文字）: {result['response'][:100]}...")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        print()
        return False


def main():
    """メインテスト"""
    print("=" * 60)
    print("LLMルーティングシステム 統合テスト")
    print("=" * 60)
    print()
    
    # ヘルスチェック
    if not test_health_check():
        print("❌ ヘルスチェック失敗。APIサーバーが起動していない可能性があります。")
        print("   Unified API（PORT=9510）を起動してください。")
        return
    
    # モデル一覧取得
    test_get_models()
    
    # テストケース1：軽量タスク（難易度分析のみ）
    test_analyze_difficulty(
        "この関数のタイポを修正して",
        {"code_context": "def hello():\n    print('helo')"}
    )
    
    # テストケース2：中量タスク（難易度分析のみ）
    test_analyze_difficulty(
        "このコードをリファクタリングして、関数を分割して",
        {
            "code_context": """
def process_data(data):
    for item in data:
        if item['type'] == 'A':
            result = item['value'] * 2
        elif item['type'] == 'B':
            result = item['value'] * 3
        else:
            result = item['value']
        print(result)
"""
        }
    )
    
    # テストケース3：高難易度タスク（難易度分析のみ）
    test_analyze_difficulty(
        "このシステムのアーキテクチャを設計して、マイクロサービス化して、パフォーマンスを最適化して",
        {
            "code_context": """
class System:
    def __init__(self):
        self.services = []
    
    def add_service(self, service):
        self.services.append(service)
    
    def process(self, data):
        results = []
        for service in self.services:
            result = service.process(data)
            results.append(result)
        return results
"""
        }
    )
    
    # 注意：実際のLLM呼び出しテストは、LM Studio/Ollamaが起動している必要があります
    print("=" * 60)
    print("注意: 実際のLLM呼び出しテストは、LM Studio/Ollamaが起動している必要があります")
    print("=" * 60)
    print()
    
    # ユーザーに確認
    user_input = input("LLM呼び出しテストを実行しますか？ (y/n): ")
    if user_input.lower() == 'y':
        # テストケース1：軽量タスク（LLM呼び出し）
        test_route_llm(
            "この関数のタイポを修正して",
            {"code_context": "def hello():\n    print('helo')"}
        )
        
        # テストケース2：速度優先設定
        test_route_llm(
            "このコードをリファクタリングして",
            {"code_context": "def hello():\n    print('hello')"},
            {"prefer_speed": True}
        )
        
        # テストケース3：品質優先設定
        test_route_llm(
            "このシステムのアーキテクチャを設計して",
            {
                "code_context": """
class System:
    def __init__(self):
        self.services = []
"""
            },
            {"prefer_quality": True}
        )
    
    print("=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
