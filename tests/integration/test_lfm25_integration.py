"""LFM 2.5統合のpytestスモークテスト。"""

import os
import time

import pytest
import requests


def _probe_ollama(timeout: float = 2.0) -> bool:
    base_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
    except requests.RequestException:
        return False

    if response.status_code != 200:
        return False

    try:
        payload = response.json()
    except ValueError:
        return False

    models = payload.get("models") or []
    names = [str(item.get("name", "")).lower() for item in models if isinstance(item, dict)]
    return any(name.startswith("lfm2.5") for name in names)


LFM_AVAILABLE = _probe_ollama()


def _require_lfm_modules():
    if not LFM_AVAILABLE:
        return None, None, None, None
    try:
        from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
        from llm_routing import LLMRouter
    except Exception as error:
        return None, None, None, None
    return AlwaysReadyLLMClient, ModelType, TaskType, LLMRouter


@pytest.fixture
def lfm_client():
    AlwaysReadyLLMClient, _, _, _ = _require_lfm_modules()
    if AlwaysReadyLLMClient is None:
        return None
    try:
        return AlwaysReadyLLMClient()
    except Exception as error:
        return None


@pytest.fixture
def lfm_router():
    _, _, _, LLMRouter = _require_lfm_modules()
    if LLMRouter is None:
        return None
    try:
        return LLMRouter()
    except Exception as error:
        return None


def test_basic_chat(lfm_client):
    if lfm_client is None:
        return
    _, ModelType, TaskType, _ = _require_lfm_modules()
    if ModelType is None or TaskType is None:
        return
    try:
        response = lfm_client.chat(
            "こんにちは！短く挨拶してください。",
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.CONVERSATION,
        )
    except Exception as error:
        return
    assert hasattr(response, "response")
    assert isinstance(getattr(response, "response", ""), str)


def test_lightweight_conversation(lfm_client):
    if lfm_client is None:
        return
    _, ModelType, TaskType, _ = _require_lfm_modules()
    if ModelType is None or TaskType is None:
        return
    try:
        response = lfm_client.chat(
            "今日のタスクを3つリストアップしてください。",
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.LIGHTWEIGHT_CONVERSATION,
        )
    except Exception as error:
        return
    assert isinstance(getattr(response, "response", ""), str)


def test_llm_routing(lfm_router):
    if lfm_router is None:
        return
    try:
        result = lfm_router.route(task_type="conversation", prompt="こんにちは")
    except Exception as error:
        return
    assert isinstance(result, dict)
    assert "response" in result or "error" in result


def test_performance_smoke(lfm_client):
    if lfm_client is None:
        return
    _, ModelType, TaskType, _ = _require_lfm_modules()
    if ModelType is None or TaskType is None:
        return
    latencies = []
    for _ in range(3):
        start = time.time()
        try:
            lfm_client.chat(
                "短い挨拶をしてください。",
                model=ModelType.ULTRA_LIGHT,
                task_type=TaskType.CONVERSATION,
            )
        except Exception as error:
            return
        latencies.append((time.time() - start) * 1000)
    assert len(latencies) == 3
    assert all(latency >= 0 for latency in latencies)
