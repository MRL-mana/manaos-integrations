"""
📚 常時起動LLM使用例集
様々な使い方のサンプルコード
"""

from always_ready_llm_client import (
    AlwaysReadyLLMClient,
    ModelType,
    TaskType,
    quick_chat
)
from llm_load_balancer import LLMLoadBalancer, ModelEndpoint, LoadBalanceStrategy
from llm_performance_monitor import LLMPerformanceMonitor


# ========================================
# 例1: 基本的な使い方
# ========================================
def example_basic_usage():
    """基本的な使い方"""
    print("=== 例1: 基本的な使い方 ===")
    
    # クライアント初期化
    client = AlwaysReadyLLMClient()
    
    # 簡単なチャット
    response = client.chat("こんにちは！")
    print(f"レスポンス: {response.response}")
    print(f"モデル: {response.model}")
    print(f"キャッシュ: {response.cached}")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")


# ========================================
# 例2: モデル選択
# ========================================
def example_model_selection():
    """モデル選択の例"""
    print("\n=== 例2: モデル選択 ===")
    
    client = AlwaysReadyLLMClient()
    
    # 軽量モデル（高速）
    response_light = client.chat(
        "短い挨拶をしてください",
        model=ModelType.LIGHT
    )
    print(f"軽量モデル: {response_light.response[:50]}... ({response_light.latency_ms:.2f}ms)")
    
    # 中型モデル（バランス）
    response_medium = client.chat(
        "Pythonでクイックソートを実装してください",
        model=ModelType.MEDIUM,
        task_type=TaskType.AUTOMATION
    )
    print(f"中型モデル: {response_medium.response[:50]}... ({response_medium.latency_ms:.2f}ms)")


# ========================================
# 例3: バッチ処理
# ========================================
def example_batch_processing():
    """バッチ処理の例"""
    print("\n=== 例3: バッチ処理 ===")
    
    client = AlwaysReadyLLMClient()
    
    messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう"
    ]
    
    results = client.batch_chat(messages, ModelType.LIGHT)
    
    for i, result in enumerate(results):
        print(f"{i+1}. {result.response[:50]}...")


# ========================================
# 例4: ストリーミング
# ========================================
def example_streaming():
    """ストリーミングの例"""
    print("\n=== 例4: ストリーミング ===")
    
    client = AlwaysReadyLLMClient()
    
    def print_chunk(chunk):
        """チャンク表示"""
        print(chunk, end="", flush=True)
    
    response = client.stream_chat(
        "短い物語を書いてください",
        ModelType.MEDIUM,
        callback=print_chunk
    )
    print(f"\n\n完全なレスポンス: {len(response)}文字")


# ========================================
# 例5: 負荷分散
# ========================================
def example_load_balancing():
    """負荷分散の例"""
    print("\n=== 例5: 負荷分散 ===")
    
    endpoints = [
        ModelEndpoint(model=ModelType.LIGHT, priority=1),
        ModelEndpoint(model=ModelType.MEDIUM, priority=2),
        ModelEndpoint(model=ModelType.HEAVY, priority=3)
    ]
    
    balancer = LLMLoadBalancer(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.ROUND_ROBIN,
        enable_fallback=True
    )
    
    response = balancer.chat("こんにちは！")
    print(f"レスポンス: {response.response}")
    print(f"使用モデル: {response.model}")
    
    # 統計情報
    stats = balancer.get_stats()
    print(f"\n統計情報:")
    for endpoint in stats["endpoints"]:
        print(f"  {endpoint['model']}: 成功率 {endpoint['success_rate']*100:.2f}%")


# ========================================
# 例6: パフォーマンス監視
# ========================================
def example_performance_monitoring():
    """パフォーマンス監視の例"""
    print("\n=== 例6: パフォーマンス監視 ===")
    
    client = AlwaysReadyLLMClient()
    monitor = LLMPerformanceMonitor(client)
    
    # テストリクエスト
    test_messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう"
    ]
    
    for message in test_messages:
        try:
            response = client.chat(message, ModelType.LIGHT)
            monitor.record(message, ModelType.LIGHT, TaskType.CONVERSATION, response=response)
        except Exception as e:
            monitor.record(message, ModelType.LIGHT, TaskType.CONVERSATION, error=e)
    
    # ダッシュボード表示
    monitor.print_dashboard()


# ========================================
# 例7: クイックチャット（最も簡単）
# ========================================
def example_quick_chat():
    """クイックチャットの例（最も簡単）"""
    print("\n=== 例7: クイックチャット ===")
    
    # 1行で呼び出し
    response = quick_chat("こんにちは！", ModelType.LIGHT)
    print(f"レスポンス: {response}")


# ========================================
# 例8: エラーハンドリング
# ========================================
def example_error_handling():
    """エラーハンドリングの例"""
    print("\n=== 例8: エラーハンドリング ===")
    
    client = AlwaysReadyLLMClient()
    
    try:
        response = client.chat("テストメッセージ", ModelType.LIGHT)
        print(f"成功: {response.response}")
    except Exception as e:
        print(f"エラー: {e}")
        # フォールバック処理など


# ========================================
# 例9: キャッシュ無効化
# ========================================
def example_cache_control():
    """キャッシュ制御の例"""
    print("\n=== 例9: キャッシュ制御 ===")
    
    client = AlwaysReadyLLMClient()
    
    # キャッシュ有効
    response1 = client.chat("同じメッセージ", use_cache=True)
    print(f"1回目（キャッシュ有効）: {response1.cached}")
    
    # キャッシュ無効
    response2 = client.chat("同じメッセージ", use_cache=False)
    print(f"2回目（キャッシュ無効）: {response2.cached}")


# ========================================
# 例10: タスクタイプ別使用
# ========================================
def example_task_types():
    """タスクタイプ別使用の例"""
    print("\n=== 例10: タスクタイプ別使用 ===")
    
    client = AlwaysReadyLLMClient()
    
    # 会話
    response_conv = client.chat(
        "こんにちは！",
        task_type=TaskType.CONVERSATION
    )
    print(f"会話: {response_conv.response[:50]}...")
    
    # 推論
    response_reason = client.chat(
        "この問題を分析してください",
        task_type=TaskType.REASONING,
        model=ModelType.MEDIUM
    )
    print(f"推論: {response_reason.response[:50]}...")
    
    # 自動処理
    response_auto = client.chat(
        "コードを生成してください",
        task_type=TaskType.AUTOMATION,
        model=ModelType.MEDIUM
    )
    print(f"自動処理: {response_auto.response[:50]}...")


# ========================================
# メイン実行
# ========================================
if __name__ == "__main__":
    print("📚 常時起動LLM使用例集\n")
    
    # 各例を実行
    example_basic_usage()
    example_model_selection()
    example_batch_processing()
    # example_streaming()  # ストリーミングは時間がかかるのでコメントアウト
    example_load_balancing()
    example_performance_monitoring()
    example_quick_chat()
    example_error_handling()
    example_cache_control()
    example_task_types()
    
    print("\n✅ 全ての例を実行しました！")






















