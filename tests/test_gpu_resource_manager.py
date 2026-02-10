#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: GPUリソース管理システム
"""

import pytest
import asyncio
from gpu_resource_manager import GPUResourceManager, GPURequest, GPUContext
from datetime import datetime


@pytest.mark.asyncio
class TestGPUResourceManager:
    """GPUリソース管理のテスト"""
    
    async def test_acquire_and_release(self):
        """GPUリソースの取得と解放のテスト"""
        manager = GPUResourceManager(max_concurrent=2)
        
        request1 = GPURequest(
            request_id="req1",
            process_id=123,
            model_name="test-model",
            priority=5
        )
        
        # リソースを取得
        acquired = await manager.acquire_gpu(request1)
        assert acquired == True
        
        status = await manager.get_status()
        assert status["active_requests"] == 1
        
        # リソースを解放
        await manager.release_gpu("req1")
        
        status = await manager.get_status()
        assert status["active_requests"] == 0
    
    async def test_max_concurrent(self):
        """同時実行数の制限テスト"""
        manager = GPUResourceManager(max_concurrent=2)
        
        # 2つのリクエストを取得
        request1 = GPURequest(request_id="req1", process_id=1, model_name="model1")
        request2 = GPURequest(request_id="req2", process_id=2, model_name="model2")
        
        assert await manager.acquire_gpu(request1) == True
        assert await manager.acquire_gpu(request2) == True
        
        # 3つ目は待機キューに入る
        request3 = GPURequest(request_id="req3", process_id=3, model_name="model3")
        assert await manager.acquire_gpu(request3) == False
        
        status = await manager.get_status()
        assert status["active_requests"] == 2
        assert status["waiting_requests"] == 1
    
    async def test_priority_queue(self):
        """優先度キューンのテスト"""
        manager = GPUResourceManager(max_concurrent=1)
        
        # 低優先度リクエスト
        request1 = GPURequest(request_id="req1", process_id=1, model_name="model1", priority=1)
        await manager.acquire_gpu(request1)
        
        # 高優先度リクエスト
        request2 = GPURequest(request_id="req2", process_id=2, model_name="model2", priority=10)
        await manager.acquire_gpu(request2)
        
        # リクエスト1を解放すると、リクエスト2が開始される
        await manager.release_gpu("req1")
        
        status = await manager.get_status()
        assert status["active_requests"] == 1
        assert "req2" in status["active_request_ids"]


@pytest.mark.asyncio
async def test_gpu_context():
    """GPUコンテキストマネージャーのテスト"""
    manager = GPUResourceManager(max_concurrent=1)
    
    request = GPURequest(
        request_id="req1",
        process_id=123,
        model_name="test-model"
    )
    
    async with GPUContext(manager, request) as ctx:
        assert ctx.acquired == True
        status = await manager.get_status()
        assert status["active_requests"] == 1
    
    # コンテキスト終了後は解放される
    status = await manager.get_status()
    assert status["active_requests"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








