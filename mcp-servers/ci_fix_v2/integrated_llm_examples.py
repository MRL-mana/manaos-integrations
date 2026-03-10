"""
📚 統合拡張版LLM使用例集
Obsidian、Slack、Google Driveなどとの統合例
"""

from always_ready_llm_integrated import (
    IntegratedLLMClient,
    integrated_chat,
    ModelType,
    TaskType
)


# ========================================
# 例1: Obsidian自動保存
# ========================================
def example_obsidian_auto_save():
    """Obsidian自動保存の例"""
    print("=== 例1: Obsidian自動保存 ===")
    
    client = IntegratedLLMClient(
        auto_save_obsidian=True,
        auto_notify_slack=False
    )
    
    response = client.chat(
        "Pythonでクイックソートを実装してください",
        ModelType.MEDIUM,
        TaskType.AUTOMATION
    )
    
    print(f"レスポンス: {response.response[:100]}...")
    print(f"Obsidian保存: {response.integration_results.get('obsidian', {})}")  # type: ignore[union-attr]


# ========================================
# 例2: Slack通知付き
# ========================================
def example_slack_notification():
    """Slack通知の例"""
    print("\n=== 例2: Slack通知 ===")
    
    client = IntegratedLLMClient(
        auto_save_obsidian=True,
        auto_notify_slack=True,
        slack_channel="#llm-notifications"
    )
    
    response = client.chat(
        "重要な質問: 今日の天気は？",
        ModelType.LIGHT,
        TaskType.CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"Slack通知: {response.integration_results.get('slack', {})}")  # type: ignore[union-attr]


# ========================================
# 例3: Google Drive保存
# ========================================
def example_drive_save():
    """Google Drive保存の例"""
    print("\n=== 例3: Google Drive保存 ===")
    
    client = IntegratedLLMClient(
        auto_save_drive=True
    )
    
    response = client.chat(
        "長文の記事を書いてください",
        ModelType.HEAVY,
        TaskType.GENERATION
    )
    
    print(f"レスポンス: {response.response[:100]}...")
    print(f"Drive保存: {response.integration_results.get('drive', {})}")  # type: ignore[union-attr]


# ========================================
# 例4: Mem0メモリ保存
# ========================================
def example_memory_save():
    """Mem0メモリ保存の例"""
    print("\n=== 例4: Mem0メモリ保存 ===")
    
    client = IntegratedLLMClient(
        auto_save_memory=True
    )
    
    response = client.chat(
        "私の名前はマナです",
        ModelType.LIGHT,
        TaskType.CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"メモリ保存: {response.integration_results.get('memory', {})}")  # type: ignore[union-attr]


# ========================================
# 例5: 全統合機能使用
# ========================================
def example_full_integration():
    """全統合機能の例"""
    print("\n=== 例5: 全統合機能 ===")
    
    client = IntegratedLLMClient(
        auto_save_obsidian=True,
        auto_notify_slack=True,
        auto_save_drive=True,
        auto_save_memory=True,
        obsidian_folder="LLM/FullIntegration",
        slack_channel="#llm-notifications"
    )
    
    response = client.chat(
        "重要な質問: 今日のタスクを整理してください",
        ModelType.MEDIUM,
        TaskType.REASONING
    )
    
    print(f"レスポンス: {response.response[:100]}...")
    print(f"\n統合結果:")
    for service, result in response.integration_results.items():  # type: ignore[union-attr]
        print(f"  {service}: {result.get('success', False)}")


# ========================================
# 例6: クイック統合チャット
# ========================================
def example_quick_integrated():
    """クイック統合チャットの例"""
    print("\n=== 例6: クイック統合チャット ===")
    
    # 1行で統合チャット
    response = integrated_chat(
        "こんにちは！",
        ModelType.LIGHT,
        save_to_obsidian=True,
        notify_slack=False
    )
    
    print(f"レスポンス: {response.response}")


# ========================================
# 例7: バッチ処理 + 統合
# ========================================
def example_batch_integration():
    """バッチ処理 + 統合の例"""
    print("\n=== 例7: バッチ処理 + 統合 ===")
    
    client = IntegratedLLMClient(
        auto_save_obsidian=True
    )
    
    messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう"
    ]
    
    results = client.batch_chat_with_integration(
        messages,
        ModelType.LIGHT,
        TaskType.CONVERSATION
    )
    
    for i, result in enumerate(results):
        print(f"{i+1}. {result.response[:50]}...")
        print(f"   Obsidian: {result.integration_results.get('obsidian', {}).get('success', False)}")  # type: ignore[union-attr]


# ========================================
# メイン実行
# ========================================
if __name__ == "__main__":
    print("統合拡張版LLM使用例集\n")
    
    # 各例を実行
    example_obsidian_auto_save()
    # example_slack_notification()  # Slack設定が必要
    # example_drive_save()  # Google Drive設定が必要
    # example_memory_save()  # Mem0設定が必要
    # example_full_integration()  # 全設定が必要
    example_quick_integrated()
    example_batch_integration()
    
    print("\n全ての例を実行しました！")






















