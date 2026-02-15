"""
Cursor × ローカルLLM統合 使用例
"""

import os
import requests
import json
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


def analyze_difficulty(prompt: str, code_context: Optional[str] = None) -> Dict[str, Any]:
    """
    プロンプトの難易度を分析
    
    Args:
        prompt: ユーザーのプロンプト
        code_context: 関連コード（オプション）
    
    Returns:
        難易度分析結果
    """
    url = f"{UNIFIED_API_URL}/api/llm/analyze"
    
    data = {
        "prompt": prompt,
        "context": {}
    }
    
    if code_context:
        data["context"]["code_context"] = code_context
    
    response = requests.post(url, json=data)
    return response.json()


def route_llm(
    prompt: str,
    code_context: Optional[str] = None,
    prefer_speed: bool = True,
    prefer_quality: bool = False
) -> Dict[str, Any]:
    """
    LLMリクエストをルーティングして実行
    
    Args:
        prompt: ユーザーのプロンプト
        code_context: 関連コード（オプション）
        prefer_speed: 速度優先
        prefer_quality: 品質優先
    
    Returns:
        ルーティング結果
    """
    url = f"{UNIFIED_API_URL}/api/llm/route-enhanced"
    
    data = {
        "prompt": prompt,
        "context": {},
        "preferences": {
            "prefer_speed": prefer_speed,
            "prefer_quality": prefer_quality
        }
    }
    
    if code_context:
        data["context"]["code_context"] = code_context
    
    response = requests.post(url, json=data)
    return response.json()


def get_available_models() -> Dict[str, Any]:
    """利用可能なモデル一覧を取得"""
    url = f"{UNIFIED_API_URL}/api/llm/models-enhanced"
    response = requests.get(url)
    return response.json()


# 使用例
if __name__ == "__main__":
    print("=" * 60)
    print("Cursor × ローカルLLM統合 使用例")
    print("=" * 60)
    print()
    
    # 例1: 難易度分析
    print("[例1] 難易度分析")
    print("-" * 60)
    
    prompt1 = "この関数のタイポを修正して"
    code1 = "def hello():\n    print('helo')"
    
    result1 = analyze_difficulty(prompt1, code1)
    print(f"プロンプト: {prompt1}")
    print(f"難易度スコア: {result1.get('difficulty_score', 0):.2f}")
    print(f"難易度レベル: {result1.get('difficulty_level')}")
    print(f"推奨モデル: {result1.get('recommended_model')}")
    print()
    
    # 例2: ルーティング実行（軽量タスク）
    print("[例2] ルーティング実行（軽量タスク）")
    print("-" * 60)
    
    prompt2 = "この関数のタイポを修正して"
    code2 = "def hello():\n    print('helo')"
    
    try:
        result2 = route_llm(prompt2, code2, prefer_speed=True)
        print(f"プロンプト: {prompt2}")
        print(f"選択モデル: {result2.get('model')}")
        print(f"難易度スコア: {result2.get('difficulty_score', 0):.2f}")
        print(f"理由: {result2.get('reasoning')}")
        if result2.get('response'):
            print(f"応答（最初の100文字）: {result2['response'][:100]}...")
        print(f"レスポンス時間: {result2.get('response_time_ms', 0)}ms")
    except Exception as e:
        print(f"エラー: {e}")
        print("LM Studio/Ollamaが起動しているか確認してください")
    print()
    
    # 例3: ルーティング実行（高難易度タスク）
    print("[例3] ルーティング実行（高難易度タスク）")
    print("-" * 60)
    
    prompt3 = "このシステムのアーキテクチャを設計して、マイクロサービス化して、パフォーマンスを最適化して"
    code3 = """
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
    
    try:
        result3 = route_llm(prompt3, code3, prefer_quality=True)
        print(f"プロンプト: {prompt3[:50]}...")
        print(f"選択モデル: {result3.get('model')}")
        print(f"難易度スコア: {result3.get('difficulty_score', 0):.2f}")
        print(f"理由: {result3.get('reasoning')}")
    except Exception as e:
        print(f"エラー: {e}")
        print("LM Studio/Ollamaが起動しているか確認してください")
    print()
    
    # 例4: 利用可能なモデル一覧
    print("[例4] 利用可能なモデル一覧")
    print("-" * 60)
    
    try:
        models = get_available_models()
        print("利用可能なモデル:")
        for model in models.get('models', []):
            print(f"  - {model}")
    except Exception as e:
        print(f"エラー: {e}")
    
    print()
    print("=" * 60)
    print("使用例完了")
    print("=" * 60)



















