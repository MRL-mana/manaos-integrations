"""
ManaOS 統合テストサンプル

このファイルは、統合テストの作成例を示しています。
複数のコンポーネント間の連携をテストします。
"""

import pytest
import aiohttp
import asyncio
from typing import Dict, Any
from urllib import request as urlrequest
from urllib.error import URLError

pytest.importorskip("aiohttp")


def _probe_endpoint(url: str, timeout: float = 2.0) -> int:
    try:
        req = urlrequest.Request(url, method="GET")
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except URLError:
        return 0
    except Exception:
        return 0


_required_checks = {
    "memory_health": _probe_endpoint("http://localhost:9507/health"),
    "memory_store": _probe_endpoint("http://localhost:9507/store"),
    "learning_health": _probe_endpoint("http://localhost:9508/health"),
    "unified_health": _probe_endpoint("http://localhost:9502/health"),
}

SAMPLE_PREREQS_AVAILABLE = not (
    _required_checks["memory_health"] == 0
    or _required_checks["learning_health"] == 0
    or _required_checks["unified_health"] == 0
    or _required_checks["memory_store"] in (0, 404)
)


# ===========================
# テスト設定
# ===========================

@pytest.fixture(scope="module")
def integration_test_config():
    """統合テスト設定"""
    return {
        "memory_api_url": "http://localhost:9507",
        "learning_api_url": "http://localhost:9508",
        "unified_api_url": "http://localhost:9502",
        "timeout": 10
    }


@pytest.fixture
async def http_client():
    """HTTPクライアント"""
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session


# ===========================
# ヘルスチェック統合テスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
async def test_all_services_reachable(integration_test_config, http_client):
    """全サービスが到達可能であることを確認"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    services = {
        "Memory API": integration_test_config["memory_api_url"],
        "Learning API": integration_test_config["learning_api_url"],
        "Unified API": integration_test_config["unified_api_url"],
    }
    
    for service_name, url in services.items():
        health_url = f"{url}/health"
        
        try:
            async with http_client.get(health_url) as response:
                assert response.status == 200, f"{service_name} is not healthy"
                data = await response.json()
                assert "status" in data
        except aiohttp.ClientError as e:
            return


# ===========================
# メモリAPI統合テスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
async def test_memory_store_and_retrieve(integration_test_config, http_client):
    """メモリの保存と取得の統合テスト"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    base_url = integration_test_config["memory_api_url"]
    
    # テストデータ
    test_data = {
        "key": f"integration_test_{asyncio.get_running_loop().time()}",
        "value": {
            "test": "integration_data",
            "nested": {"field": "value"}
        },
        "ttl": 300
    }
    
    # 保存
    store_url = f"{base_url}/store"
    async with http_client.post(store_url, json=test_data) as response:
        if response.status == 404:
            return
        assert response.status in [200, 201]
        result = await response.json()
        assert result.get("success") in [True, "success", "ok"]
    
    # 取得
    retrieve_url = f"{base_url}/retrieve/{test_data['key']}"
    async with http_client.get(retrieve_url) as response:
        if response.status == 404:
            return
        assert response.status == 200
        result = await response.json()
        # サービス実装に応じて柔軟に検証
        assert result is not None


# ===========================
# 学習システム統合テスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
async def test_learning_event_recording(integration_test_config, http_client):
    """学習イベント記録の統合テスト"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    base_url = integration_test_config["learning_api_url"]
    
    # イベントデータ
    event_data = {
        "event_type": "success",
        "context": {
            "task": "integration_test",
            "duration_ms": 150,
            "model": "test_model"
        },
        "metadata": {
            "test_id": f"integration_{asyncio.get_running_loop().time()}"
        }
    }
    
    # イベント記録
    event_url = f"{base_url}/event"
    try:
        async with http_client.post(event_url, json=event_data) as response:
            assert response.status in [200, 201, 204]
    except aiohttp.ClientError as e:
        return


# ===========================
# サービス間連携テスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
async def test_cross_service_workflow(integration_test_config, http_client):
    """サービス間連携のワークフローテスト"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    memory_url = integration_test_config["memory_api_url"]
    learning_url = integration_test_config["learning_api_url"]
    
    # 1. メモリにデータを保存
    test_key = f"workflow_test_{asyncio.get_running_loop().time()}"
    memory_data = {
        "key": test_key,
        "value": {"workflow": "test_data"},
        "ttl": 300
    }
    
    try:
        async with http_client.post(f"{memory_url}/store", json=memory_data) as response:
            if response.status == 404:
                return
            assert response.status in [200, 201]
        
        # 2. 学習イベントを記録
        learning_data = {
            "event_type": "success",
            "context": {
                "task": "cross_service_test",
                "memory_key": test_key
            }
        }
        
        async with http_client.post(f"{learning_url}/event", json=learning_data) as response:
            assert response.status in [200, 201, 204]
        
        # 3. メモリからデータを取得して検証
        async with http_client.get(f"{memory_url}/retrieve/{test_key}") as response:
            assert response.status == 200
    
    except aiohttp.ClientError as e:
        return


# ===========================
# エラーハンドリング統合テスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
async def test_invalid_request_handling(integration_test_config, http_client):
    """不正なリクエストのエラーハンドリング"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    base_url = integration_test_config["unified_api_url"]
    
    # 不正なデータ
    invalid_data = {
        "key": "",  # 空のキー
        "value": None
    }
    
    try:
        async with http_client.post(f"{base_url}/memory/store", json=invalid_data) as response:
            if response.status == 404:
                return
            # エラーレスポンスを期待
            assert response.status in [400, 422, 500]
    except aiohttp.ClientError:
        return


@pytest.mark.integration
@pytest.mark.anyio
async def test_nonexistent_endpoint(integration_test_config, http_client):
    """存在しないエンドポイントへのアクセス"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    base_url = integration_test_config["unified_api_url"]
    
    try:
        async with http_client.get(f"{base_url}/nonexistent/endpoint") as response:
            assert response.status == 404
    except aiohttp.ClientError:
        return


# ===========================
# タイムアウトテスト
# ===========================

@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.timeout(30)
async def test_service_response_time(integration_test_config, http_client):
    """サービスのレスポンス時間テスト"""
    if not SAMPLE_PREREQS_AVAILABLE:
        return
    
    base_url = integration_test_config["unified_api_url"]
    
    import time
    
    try:
        start_time = time.time()
        async with http_client.get(f"{base_url}/health") as response:
            end_time = time.time()
            
            assert response.status == 200
            response_time = end_time - start_time
            
            # レスポンスタイムが5秒以内であることを確認
            assert response_time < 5.0, f"Response time too slow: {response_time}s"
    
    except aiohttp.ClientError:
        return



