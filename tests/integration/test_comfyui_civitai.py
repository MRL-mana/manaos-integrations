"""ComfyUIとCivitAI統合のpytestスモークテスト。"""

import os
from pathlib import Path

import pytest


def _load_dotenv_if_exists():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        pass


def test_comfyui_integration_smoke():
    _load_dotenv_if_exists()
    try:
        from comfyui_integration import ComfyUIIntegration
    except Exception as exc:
        pytest.skip(f"ComfyUIIntegrationを読み込めないためスキップ: {exc}")

    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    try:
        comfyui = ComfyUIIntegration(base_url=comfyui_url)
        available = comfyui.is_available()
    except Exception as exc:
        pytest.skip(f"ComfyUI初期化/疎通に失敗したためスキップ: {exc}")
    assert isinstance(available, bool)


def test_civitai_integration_smoke():
    _load_dotenv_if_exists()
    civitai_key = os.getenv("CIVITAI_API_KEY", "test-civitai-key")

    try:
        from civitai_integration import CivitAIIntegration
        civitai = CivitAIIntegration(api_key=civitai_key)
        available = civitai.is_available()
    except Exception as exc:
        pytest.skip(f"CivitAI初期化/疎通に失敗したためスキップ: {exc}")
    assert isinstance(available, bool)

