"""超統合拡張版テスト"""
from always_ready_llm_ultra_integrated import UltraIntegratedLLMClient, ModelType

print("超統合拡張版テスト...")
client = UltraIntegratedLLMClient(
    enable_image_generation=False,
    enable_model_search=False,
    enable_notification_hub=False,
    auto_save_obsidian=False
)

result = client.full_integration_chat(
    "こんにちは！短く挨拶してください。",
    ModelType.LIGHT,
    generate_image=False,
    notify=False
)

print(f"成功: {result['chat'].response[:50]}...")
print(f"統合機能数: {len(result['integrations'])}")
print("テスト完了！")






















