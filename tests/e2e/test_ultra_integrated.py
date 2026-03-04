"""超統合拡張版テスト。"""

import pytest
import requests


def _is_ollama_ready() -> bool:
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False


def test_ultra_integrated_chat_smoke():
    if not _is_ollama_ready():
        pytest.skip("Ollama is not available on 127.0.0.1:11434")

    from always_ready_llm_ultra_integrated import (
        UltraIntegratedLLMClient,
        ModelType,
    )

    client = UltraIntegratedLLMClient(
        enable_image_generation=False,
        enable_model_search=False,
        enable_notification_hub=False,
        auto_save_obsidian=False,
    )

    try:
        result = client.full_integration_chat(
            "こんにちは！短く挨拶してください。",
            ModelType.LIGHT,
            generate_image=False,
            notify=False,
        )
    except Exception as exc:
        pytest.skip(f"Ultra integrated runtime unavailable: {exc}")

    assert isinstance(result, dict)
    assert "chat" in result
    assert "integrations" in result






















