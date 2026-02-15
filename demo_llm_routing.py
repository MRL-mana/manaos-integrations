"""
LLMルーティングシステム デモスクリプト
実際の使用例をデモンストレーション
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

# APIエンドポイント
UNIFIED_API_URL = os.getenv(
    "MANAOS_INTEGRATION_API_URL",
    f"http://127.0.0.1:{UNIFIED_API_PORT}",
).rstrip("/")


def print_section(title: str):
    """セクションタイトルを表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result: Dict[str, Any], title: str = "結果"):
    """結果を整形して表示"""
    print(f"\n[{title}]")
    print("-" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("-" * 60)


def demo_analyze_difficulty():
    """難易度分析のデモ"""
    print_section("デモ1: 難易度分析")
    
    test_cases = [
        {
            "name": "軽量タスク",
            "prompt": "この関数のタイポを修正して",
            "code_context": "def hello():\n    print('helo')"
        },
        {
            "name": "中量タスク",
            "prompt": "このコードをリファクタリングして、関数を分割して",
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
        },
        {
            "name": "高難易度タスク",
            "prompt": "このシステムのアーキテクチャを設計して、マイクロサービス化して、パフォーマンスを最適化して",
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
    ]
    
    for test_case in test_cases:
        print(f"\n📋 {test_case['name']}")
        print(f"プロンプト: {test_case['prompt']}")
        
        try:
            response = requests.post(
                f"{UNIFIED_API_URL}/api/llm/analyze",
                json={
                    "prompt": test_case["prompt"],
                    "context": {
                        "code_context": test_case["code_context"]
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 難易度スコア: {result.get('difficulty_score', 0):.2f}")
                print(f"✅ 難易度レベル: {result.get('difficulty_level')}")
                print(f"✅ 推奨モデル: {result.get('recommended_model')}")
            else:
                print(f"❌ エラー: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 接続エラー: {e}")
            print("   APIサーバーが起動しているか確認してください")


def demo_route_llm():
    """LLMルーティングのデモ"""
    print_section("デモ2: LLMルーティング実行")
    
    test_cases = [
        {
            "name": "軽量タスク（速度優先）",
            "prompt": "この関数のタイポを修正して",
            "code_context": "def hello():\n    print('helo')",
            "preferences": {"prefer_speed": True}
        },
        {
            "name": "高難易度タスク（品質優先）",
            "prompt": "このシステムのアーキテクチャを設計して",
            "code_context": """
class System:
    def __init__(self):
        self.services = []
""",
            "preferences": {"prefer_quality": True}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 {test_case['name']}")
        print(f"プロンプト: {test_case['prompt']}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{UNIFIED_API_URL}/api/llm/route-enhanced",
                json={
                    "prompt": test_case["prompt"],
                    "context": {
                        "code_context": test_case["code_context"]
                    },
                    "preferences": test_case["preferences"]
                },
                timeout=300
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 選択モデル: {result.get('model')}")
                print(f"✅ 難易度スコア: {result.get('difficulty_score', 0):.2f}")
                print(f"✅ 難易度レベル: {result.get('difficulty_level')}")
                print(f"✅ 理由: {result.get('reasoning')}")
                print(f"✅ レスポンス時間: {result.get('response_time_ms', 0)}ms")
                print(f"✅ 実際の経過時間: {elapsed_time:.2f}秒")
                
                if result.get('response'):
                    response_preview = result['response'][:200]
                    print(f"✅ 応答（最初の200文字）: {response_preview}...")
                
                if result.get('success'):
                    print("✅ 成功")
                else:
                    print(f"❌ 失敗: {result.get('error')}")
            else:
                print(f"❌ エラー: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 接続エラー: {e}")
            print("   LM Studio/Ollamaが起動しているか確認してください")


def demo_get_models():
    """モデル一覧取得のデモ"""
    print_section("デモ3: 利用可能なモデル一覧")
    
    try:
        response = requests.get(
            f"{UNIFIED_API_URL}/api/llm/models-enhanced",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            models = result.get('models', [])
            
            print(f"✅ 利用可能なモデル数: {len(models)}")
            print("\nモデル一覧:")
            for i, model in enumerate(models, 1):
                print(f"  {i}. {model}")
        else:
            print(f"❌ エラー: HTTP {response.status_code}")
            print(f"   レスポンス: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 接続エラー: {e}")
        print("   APIサーバーが起動しているか確認してください")


def check_api_health():
    """APIサーバーのヘルスチェック"""
    print_section("ヘルスチェック")
    
    # 統合APIサーバー
    try:
        response = requests.get(f"{UNIFIED_API_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ 統合APIサーバー: 起動中")
        else:
            print(f"⚠️  統合APIサーバー: HTTP {response.status_code}")
    except Exception:
        print("❌ 統合APIサーバー: 接続不可")
        print(f"   URL: {UNIFIED_API_URL}")
    
    # LLMルーティング（Unified API内）
    try:
        response = requests.get(f"{UNIFIED_API_URL}/api/llm/health", timeout=2)
        if response.status_code == 200:
            print("✅ LLMルーティングAPI: 起動中")
        else:
            print(f"⚠️  LLMルーティングAPI: HTTP {response.status_code}")
    except Exception:
        print("❌ LLMルーティングAPI: 接続不可")
        print(f"   URL: {UNIFIED_API_URL}/api/llm/health")


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("  LLMルーティングシステム デモ")
    print("=" * 60)
    
    # ヘルスチェック
    check_api_health()
    
    # デモ実行
    print("\n" + "=" * 60)
    print("  デモを開始します")
    print("=" * 60)
    
    # デモ1: 難易度分析
    demo_analyze_difficulty()
    
    # デモ2: LLMルーティング実行
    print("\n" + "=" * 60)
    print("  注意: LLMルーティング実行にはLM Studio/Ollamaが必要です")
    print("=" * 60)
    
    user_input = input("\nLLMルーティング実行のデモを実行しますか？ (y/n): ")
    if user_input.lower() == 'y':
        demo_route_llm()
    else:
        print("LLMルーティング実行のデモをスキップしました")
    
    # デモ3: モデル一覧取得
    demo_get_models()
    
    # 完了
    print_section("デモ完了")
    print("\n✅ すべてのデモが完了しました")
    print("\n次のステップ:")
    print("  - Cursorで実際に使用してみる")
    print("  - プロンプトテンプレートを使用する")
    print("  - 詳細は README_CURSOR_LOCAL_LLM.md を参照")


if __name__ == "__main__":
    main()



















