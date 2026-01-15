"""
📚 超統合拡張版LLM使用例集
ComfyUI、CivitAI、通知ハブ、ファイル秘書など完全統合例
"""

from always_ready_llm_ultra_integrated import (
    UltraIntegratedLLMClient,
    ultra_chat,
    ModelType,
    TaskType
)


# ========================================
# 例1: LLM + 画像生成
# ========================================
def example_chat_with_image():
    """LLMチャット + 画像生成の例"""
    print("=== 例1: LLM + 画像生成 ===")
    
    client = UltraIntegratedLLMClient(
        enable_image_generation=True
    )
    
    result = client.chat_with_image_generation(
        "美しい風景を描写してください",
        ModelType.MEDIUM,
        generate_image=True
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    if result['image']:
        print(f"画像生成: {result['image'].get('success', False)}")
        print(f"プロンプトID: {result['image'].get('prompt_id')}")


# ========================================
# 例2: LLM + モデル検索
# ========================================
def example_chat_with_model_search():
    """LLMチャット + モデル検索の例"""
    print("\n=== 例2: LLM + モデル検索 ===")
    
    client = UltraIntegratedLLMClient(
        enable_model_search=True
    )
    
    result = client.chat_with_model_search(
        "リアルな人物生成モデルを探してください",
        ModelType.MEDIUM,
        search_models=True
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    if result['models']:
        print(f"モデル検索: {result['models'].get('success', False)}")
        print(f"検索結果数: {result['models'].get('count', 0)}")


# ========================================
# 例3: LLM + 通知ハブ
# ========================================
def example_chat_with_notification():
    """LLMチャット + 通知ハブの例"""
    print("\n=== 例3: LLM + 通知ハブ ===")
    
    client = UltraIntegratedLLMClient(
        enable_notification_hub=True
    )
    
    result = client.chat_with_notification_hub(
        "重要な質問: 今日のタスクを整理してください",
        ModelType.MEDIUM,
        notify=True,
        priority="important"
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    if result['notification']:
        print(f"通知: {result['notification'].get('success', False)}")


# ========================================
# 例4: LLM + ファイル整理
# ========================================
def example_chat_with_file_organization():
    """LLMチャット + ファイル整理の例"""
    print("\n=== 例4: LLM + ファイル整理 ===")
    
    client = UltraIntegratedLLMClient(
        enable_file_organization=True
    )
    
    result = client.chat_with_file_organization(
        "ダウンロードフォルダを整理してください",
        ModelType.MEDIUM,
        organize_files=True
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    if result['file_organization']:
        print(f"ファイル整理: {result['file_organization'].get('success', False)}")


# ========================================
# 例5: LLM + GitHub統合
# ========================================
def example_chat_with_github():
    """LLMチャット + GitHub統合の例"""
    print("\n=== 例5: LLM + GitHub統合 ===")
    
    client = UltraIntegratedLLMClient()
    
    result = client.chat_with_github(
        "バグ修正が必要です",
        ModelType.MEDIUM,
        create_issue=True
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    if result['github']:
        print(f"GitHub Issue: {result['github'].get('success', False)}")


# ========================================
# 例6: 全統合機能使用
# ========================================
def example_full_integration():
    """全統合機能の例"""
    print("\n=== 例6: 全統合機能 ===")
    
    client = UltraIntegratedLLMClient(
        enable_image_generation=True,
        enable_model_search=True,
        enable_notification_hub=True,
        enable_file_organization=True,
        auto_save_obsidian=True,
        auto_notify_slack=True
    )
    
    result = client.full_integration_chat(
        "美しい風景を描写して、関連するモデルも検索してください",
        ModelType.MEDIUM,
        generate_image=True,
        search_models=True,
        notify=True,
        organize_files=False
    )
    
    print(f"チャット: {result['chat'].response[:100]}...")
    print(f"\n統合結果:")
    for service, service_result in result['integrations'].items():
        if service_result:
            print(f"  {service}: {service_result.get('success', False)}")


# ========================================
# 例7: クイック超統合チャット
# ========================================
def example_quick_ultra():
    """クイック超統合チャットの例"""
    print("\n=== 例7: クイック超統合チャット ===")
    
    # 1行で超統合チャット
    result = ultra_chat(
        "こんにちは！",
        ModelType.LIGHT,
        generate_image=False,
        notify=False
    )
    
    print(f"レスポンス: {result['chat'].response[:100]}...")


# ========================================
# メイン実行
# ========================================
if __name__ == "__main__":
    print("超統合拡張版LLM使用例集\n")
    
    # 各例を実行
    example_chat_with_image()
    example_chat_with_model_search()
    example_chat_with_notification()
    example_chat_with_file_organization()
    example_chat_with_github()
    example_full_integration()
    example_quick_ultra()
    
    print("\n全ての例を実行しました！")






















