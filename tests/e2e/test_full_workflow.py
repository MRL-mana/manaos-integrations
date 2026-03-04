"""
ManaOS E2Eテスト

このモジュールは、ManaOS統合システムのエンドツーエンドテストを実行します。
実際のサービス間連携をテストし、統合の整合性を検証します。
"""

import pytest
import asyncio
import aiohttp
import time
from typing import Dict, Any, List
import os


# ===========================
# テスト設定
# ===========================

class E2ETestConfig:
    """E2Eテスト設定"""
    
    # サービスエンドポイント
    UNIFIED_API_URL = os.environ.get("UNIFIED_API_URL", "http://localhost:9502")
    MRL_MEMORY_URL = os.environ.get("MRL_MEMORY_URL", "http://localhost:9507")
    LEARNING_SYSTEM_URL = os.environ.get("LEARNING_SYSTEM_URL", "http://localhost:9508")
    LLM_ROUTING_URL = os.environ.get("LLM_ROUTING_URL", "http://localhost:9509")
    
    # タイムアウト設定
    REQUEST_TIMEOUT = 30
    SERVICE_STARTUP_TIMEOUT = 60
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAY = 2


@pytest.fixture(scope="session")
async def http_session():
    """HTTP セッションフィクスチャ"""
    timeout = aiohttp.ClientTimeout(total=E2ETestConfig.REQUEST_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session


@pytest.fixture(scope="session")
async def wait_for_services():
    """サービスの起動を待機"""
    services = {
        "Unified API": E2ETestConfig.UNIFIED_API_URL,
        "MRL Memory": E2ETestConfig.MRL_MEMORY_URL,
        "Learning System": E2ETestConfig.LEARNING_SYSTEM_URL,
        "LLM Routing": E2ETestConfig.LLM_ROUTING_URL,
    }
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        for service_name, url in services.items():
            health_url = f"{url}/health"
            attempts = 0
            
            while attempts < E2ETestConfig.MAX_RETRIES:
                try:
                    async with session.get(health_url, timeout=5) as response:
                        if response.status == 200:
                            print(f"✅ {service_name} is ready")
                            break
                except Exception as e:
                    attempts += 1
                    if attempts >= E2ETestConfig.MAX_RETRIES:
                        pytest.skip(f"❌ {service_name} not available: {e}")
                    await asyncio.sleep(E2ETestConfig.RETRY_DELAY)
            
            if time.time() - start_time > E2ETestConfig.SERVICE_STARTUP_TIMEOUT:
                pytest.skip("Services startup timeout exceeded")


# ===========================
# ヘルスチェックテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_all_services_healthy(http_session, wait_for_services):
    """全サービスのヘルスチェック"""
    services = {
        "Unified API": E2ETestConfig.UNIFIED_API_URL,
        "MRL Memory": E2ETestConfig.MRL_MEMORY_URL,
        "Learning System": E2ETestConfig.LEARNING_SYSTEM_URL,
        "LLM Routing": E2ETestConfig.LLM_ROUTING_URL,
    }
    
    for service_name, url in services.items():
        health_url = f"{url}/health"
        async with http_session.get(health_url) as response:
            assert response.status == 200, f"{service_name} is not healthy"
            data = await response.json()
            assert data.get("status") in ["healthy", "ok"], f"{service_name} status is {data.get('status')}"


# ===========================
# メモリ管理フローテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_memory_store_and_retrieve_flow(http_session, wait_for_services):
    """メモリの保存と取得フロー"""
    
    # 1. データを保存
    store_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/store"
    test_data = {
        "key": f"e2e_test_{int(time.time())}",
        "value": {
            "test": "data",
            "timestamp": time.time(),
            "nested": {
                "field": "value"
            }
        },
        "ttl": 3600,
        "tags": ["e2e", "test"]
    }
    
    async with http_session.post(store_url, json=test_data) as response:
        assert response.status == 201, "Failed to store memory"
        store_result = await response.json()
        assert store_result.get("success") == True
        stored_key = store_result.get("key")
    
    # 2. データを取得
    retrieve_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/retrieve/{stored_key}"
    async with http_session.get(retrieve_url) as response:
        assert response.status == 200, "Failed to retrieve memory"
        retrieve_result = await response.json()
        assert retrieve_result.get("found") == True
        assert retrieve_result.get("key") == stored_key
        assert retrieve_result.get("value") is not None
    
    # 3. データの整合性チェック
    retrieved_value = retrieve_result.get("value")
    assert retrieved_value.get("test") == "data"
    assert retrieved_value.get("nested", {}).get("field") == "value"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_memory_ttl_expiration(http_session, wait_for_services):
    """メモリのTTL有効期限テスト"""
    
    # 1. 短いTTLでデータを保存
    store_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/store"
    test_data = {
        "key": f"e2e_ttl_test_{int(time.time())}",
        "value": {"test": "ttl_data"},
        "ttl": 2,  # 2秒後に期限切れ
    }
    
    async with http_session.post(store_url, json=test_data) as response:
        assert response.status == 201
        store_result = await response.json()
        stored_key = store_result.get("key")
    
    # 2. すぐに取得（成功するはず）
    retrieve_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/retrieve/{stored_key}"
    async with http_session.get(retrieve_url) as response:
        assert response.status == 200
        result = await response.json()
        assert result.get("found") == True
    
    # 3. TTL経過後に取得（失敗するはず）
    await asyncio.sleep(3)
    async with http_session.get(retrieve_url) as response:
        result = await response.json()
        assert result.get("found") == False or response.status == 404


# ===========================
# 学習システムフローテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_learning_event_recording_flow(http_session, wait_for_services):
    """学習イベント記録フロー"""
    
    # 1. 成功イベントを記録
    event_url = f"{E2ETestConfig.UNIFIED_API_URL}/learning/event"
    success_event = {
        "event_type": "success",
        "context": {
            "task": "e2e_test_task",
            "duration_ms": 1500,
            "model": "test-model-v1"
        },
        "metadata": {
            "test_id": f"e2e_{int(time.time())}",
            "quality_score": 0.95
        }
    }
    
    async with http_session.post(event_url, json=success_event) as response:
        assert response.status == 201
        result = await response.json()
        assert result.get("success") == True
        assert result.get("event_id") is not None
    
    # 2. 失敗イベントを記録
    failure_event = {
        "event_type": "failure",
        "context": {
            "task": "e2e_test_task",
            "error": "test_error",
            "duration_ms": 500
        }
    }
    
    async with http_session.post(event_url, json=failure_event) as response:
        assert response.status == 201
        result = await response.json()
        assert result.get("success") == True


# ===========================
# LLMルーティングフローテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_llm_routing_flow(http_session, wait_for_services):
    """LLMルーティングフロー"""
    
    route_url = f"{E2ETestConfig.UNIFIED_API_URL}/llm/route"
    
    # 1. シンプルなプロンプト（低コストモデルを使用すべき）
    simple_request = {
        "prompt": "Hello, how are you?",
        "max_tokens": 50,
        "temperature": 0.7
    }
    
    async with http_session.post(route_url, json=simple_request) as response:
        assert response.status == 200
        result = await response.json()
        assert result.get("model_used") is not None
        assert result.get("response") is not None
        assert result.get("tokens_used") > 0
        assert result.get("cost_estimate") >= 0
    
    # 2. 複雑なプロンプト（高性能モデルを使用すべき）
    complex_request = {
        "prompt": "Please analyze the following complex data and provide insights...",
        "max_tokens": 1000,
        "temperature": 0.3,
        "preferred_model": "gpt-4"
    }
    
    async with http_session.post(route_url, json=complex_request) as response:
        assert response.status == 200
        result = await response.json()
        assert result.get("reasoning") is not None


# ===========================
# 統合フローテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_full_integrated_workflow(http_session, wait_for_services):
    """完全な統合ワークフローテスト"""
    
    # シナリオ: ユーザーがLLMで質問 → 結果をメモリに保存 → 学習イベント記録
    
    # 1. LLMリクエスト
    llm_url = f"{E2ETestConfig.UNIFIED_API_URL}/llm/route"
    llm_request = {
        "prompt": "What is the capital of Japan?",
        "max_tokens": 100
    }
    
    async with http_session.post(llm_url, json=llm_request) as response:
        assert response.status == 200
        llm_result = await response.json()
        llm_response = llm_result.get("response")
        tokens_used = llm_result.get("tokens_used")
    
    # 2. 結果をメモリに保存
    memory_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/store"
    memory_data = {
        "key": f"llm_result_{int(time.time())}",
        "value": {
            "prompt": llm_request["prompt"],
            "response": llm_response,
            "tokens_used": tokens_used
        },
        "tags": ["llm", "qa"]
    }
    
    async with http_session.post(memory_url, json=memory_data) as response:
        assert response.status == 201
        memory_result = await response.json()
        memory_key = memory_result.get("key")
    
    # 3. 学習イベント記録
    learning_url = f"{E2ETestConfig.UNIFIED_API_URL}/learning/event"
    learning_data = {
        "event_type": "success",
        "context": {
            "task": "llm_qa",
            "tokens_used": tokens_used,
            "memory_key": memory_key
        }
    }
    
    async with http_session.post(learning_url, json=learning_data) as response:
        assert response.status == 201
        learning_result = await response.json()
        assert learning_result.get("success") == True
    
    # 4. メモリから結果を取得して検証
    retrieve_url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/retrieve/{memory_key}"
    async with http_session.get(retrieve_url) as response:
        assert response.status == 200
        retrieve_result = await response.json()
        assert retrieve_result.get("found") == True
        stored_value = retrieve_result.get("value")
        assert stored_value.get("prompt") == llm_request["prompt"]
        assert stored_value.get("response") == llm_response


# ===========================
# 負荷テスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_concurrent_requests_handling(http_session, wait_for_services):
    """並行リクエスト処理テスト"""
    
    # 100個の並行リクエストを送信
    async def make_request(session, request_id):
        url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/store"
        data = {
            "key": f"concurrent_test_{request_id}",
            "value": {"id": request_id}
        }
        
        try:
            async with session.post(url, json=data) as response:
                return response.status == 201
        except Exception as e:
            print(f"Request {request_id} failed: {e}")
            return False
    
    # 並行実行
    tasks = [make_request(http_session, i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    # 成功率をチェック（95%以上成功すること）
    success_rate = sum(results) / len(results) * 100
    assert success_rate >= 95, f"Success rate too low: {success_rate}%"


# ===========================
# エラーハンドリングテスト
# ===========================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_invalid_request_handling(http_session, wait_for_services):
    """不正なリクエストのエラーハンドリング"""
    
    # 1. 不正なデータ形式
    url = f"{E2ETestConfig.UNIFIED_API_URL}/memory/store"
    invalid_data = {
        "key": "",  # 空のキー（不正）
        "value": None
    }
    
    async with http_session.post(url, json=invalid_data) as response:
        assert response.status in [400, 422], "Should return bad request error"
    
    # 2. 存在しないエンドポイント
    url = f"{E2ETestConfig.UNIFIED_API_URL}/nonexistent/endpoint"
    async with http_session.get(url) as response:
        assert response.status == 404, "Should return not found error"


if __name__ == "__main__":
    # pytest実行
    pytest.main([__file__, "-v", "-s", "--tb=short"])
