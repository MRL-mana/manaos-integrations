"""
LFM 2.5使用例集
ManaOS環境でのLFM 2.5の実用的な使用例
"""

from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
from llm_routing import LLMRouter
import time


def example_1_basic_chat():
    """例1: 基本的なチャット"""
    print("="*60)
    print("例1: 基本的なチャット")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    response = client.chat(
        "こんにちは！短く挨拶してください。",
        model=ModelType.ULTRA_LIGHT,
        task_type=TaskType.CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")
    print()


def example_2_lightweight_conversation():
    """例2: 軽量会話（オフライン会話・下書き・整理）"""
    print("="*60)
    print("例2: 軽量会話（オフライン会話・下書き・整理）")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    # タスク整理
    response = client.chat(
        "今日のタスクを3つリストアップしてください。",
        model=ModelType.ULTRA_LIGHT,
        task_type=TaskType.LIGHTWEIGHT_CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")
    print()


def example_3_draft_creation():
    """例3: 下書き作成"""
    print("="*60)
    print("例3: 下書き作成")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    response = client.chat(
        "ブログ記事の下書きを作成してください。テーマは「AIの未来」です。",
        model=ModelType.ULTRA_LIGHT,
        task_type=TaskType.LIGHTWEIGHT_CONVERSATION
    )
    
    print(f"レスポンス: {response.response[:200]}...")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")
    print()


def example_4_text_organization():
    """例4: テキスト整理"""
    print("="*60)
    print("例4: テキスト整理")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    response = client.chat(
        "以下のメモを整理してください：\n- タスク1\n- タスク2\n- タスク3",
        model=ModelType.ULTRA_LIGHT,
        task_type=TaskType.LIGHTWEIGHT_CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")
    print()


def example_5_llm_routing():
    """例5: LLMルーティングシステム経由"""
    print("="*60)
    print("例5: LLMルーティングシステム経由")
    print("="*60)
    
    router = LLMRouter()
    
    # conversationタスク（自動的にLFM 2.5が優先される）
    result = router.route(
        task_type="conversation",
        prompt="こんにちは、今日はいい天気ですね。"
    )
    
    print(f"レスポンス: {result.get('response', '')[:100]}...")
    print(f"モデル: {result.get('model', '')}")
    print(f"Fallback使用: {'Yes' if result.get('fallback_used') else 'No'}")
    print()


def example_6_lightweight_routing():
    """例6: 軽量会話ルーティング"""
    print("="*60)
    print("例6: 軽量会話ルーティング")
    print("="*60)
    
    router = LLMRouter()
    
    # lightweight_conversationタスク（常駐軽量LLM専用）
    result = router.route(
        task_type="lightweight_conversation",
        prompt="メモを整理してください"
    )
    
    print(f"レスポンス: {result.get('response', '')[:100]}...")
    print(f"モデル: {result.get('model', '')}")
    print(f"Fallback使用: {'Yes' if result.get('fallback_used') else 'No'}")
    print()


def example_7_batch_processing():
    """例7: バッチ処理"""
    print("="*60)
    print("例7: バッチ処理")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう"
    ]
    
    results = client.batch_chat(
        messages=messages,
        model=ModelType.ULTRA_LIGHT,
        task_type=TaskType.CONVERSATION
    )
    
    for i, result in enumerate(results):
        print(f"{i+1}. {result.response[:50]}... ({result.latency_ms:.2f}ms)")
    print()


def example_8_performance_test():
    """例8: パフォーマンステスト"""
    print("="*60)
    print("例8: パフォーマンステスト")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    test_prompt = "短い挨拶をしてください。"
    num_iterations = 5
    latencies = []
    
    print(f"プロンプト: {test_prompt}")
    print(f"実行回数: {num_iterations}回\n")
    
    for i in range(num_iterations):
        start_time = time.time()
        response = client.chat(
            test_prompt,
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.CONVERSATION
        )
        elapsed_time = (time.time() - start_time) * 1000
        latencies.append(elapsed_time)
        print(f"実行 {i+1}/{num_iterations}: {elapsed_time:.2f}ms")
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    
    print(f"\n平均レイテンシ: {avg_latency:.2f}ms")
    print(f"最小レイテンシ: {min_latency:.2f}ms")
    print(f"最大レイテンシ: {max_latency:.2f}ms")
    print()


def example_9_japanese_quality():
    """例9: 日本語品質テスト"""
    print("="*60)
    print("例9: 日本語品質テスト")
    print("="*60)
    
    client = AlwaysReadyLLMClient()
    
    test_cases = [
        "丁寧な言葉で挨拶してください。",
        "「は」と「が」の違いを説明してください。",
        "以下のPythonコードを説明してください：\ndef hello():\n    print('Hello')"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテストケース {i}: {test_case}")
        response = client.chat(
            test_case,
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.CONVERSATION
        )
        print(f"レスポンス: {response.response[:150]}...")
    print()


def example_10_api_usage():
    """例10: API経由での使用"""
    print("="*60)
    print("例10: API経由での使用")
    print("="*60)
    
    import requests
    
    api_url = "http://127.0.0.1:9510"
    
    # LFM 2.5チャット
    response = requests.post(
        f"{api_url}/api/lfm25/chat",
        json={
            "message": "こんにちは！",
            "task_type": "conversation"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"レスポンス: {data.get('response', '')}")
        print(f"レイテンシ: {data.get('latency_ms', 0):.2f}ms")
    else:
        print(f"エラー: {response.status_code} - {response.text}")
    print()


def run_all_examples():
    """すべての例を実行"""
    print("\n" + "="*60)
    print("🚀 LFM 2.5使用例集")
    print("="*60 + "\n")
    
    examples = [
        example_1_basic_chat,
        example_2_lightweight_conversation,
        example_3_draft_creation,
        example_4_text_organization,
        example_5_llm_routing,
        example_6_lightweight_routing,
        example_7_batch_processing,
        example_8_performance_test,
        example_9_japanese_quality,
        # example_10_api_usage,  # APIサーバーが起動している場合のみ
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ エラー: {e}\n")
    
    print("="*60)
    print("✅ すべての例を実行しました")
    print("="*60)


if __name__ == "__main__":
    run_all_examples()
