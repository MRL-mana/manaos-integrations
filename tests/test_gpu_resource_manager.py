#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: GPUリソース管理システム
"""

import asyncio

import pytest

from gpu_resource_manager import GPUContext, GPURequest, GPUResourceManager


class TestGPUResourceManager:
    """GPUリソース管理のテスト"""

    def test_acquire_and_release(self):
        """GPUリソースの取得と解放のテスト"""

        async def scenario() -> None:
            manager = GPUResourceManager(max_concurrent=2)

            request1 = GPURequest(
                request_id="req1",
                process_id=123,
                model_name="test-model",
                priority=5,
            )

            acquired = await manager.acquire_gpu(request1)
            assert acquired is True

            status = await manager.get_status()
            assert status["active_requests"] == 1

            await manager.release_gpu("req1")

            status = await manager.get_status()
            assert status["active_requests"] == 0

        asyncio.run(scenario())

    def test_max_concurrent(self):
        """同時実行数の制限テスト"""

        async def scenario() -> None:
            manager = GPUResourceManager(max_concurrent=2)

            request1 = GPURequest(request_id="req1", process_id=1, model_name="model1")
            request2 = GPURequest(request_id="req2", process_id=2, model_name="model2")

            assert await manager.acquire_gpu(request1) is True
            assert await manager.acquire_gpu(request2) is True

            request3 = GPURequest(request_id="req3", process_id=3, model_name="model3")
            assert await manager.acquire_gpu(request3) is False

            status = await manager.get_status()
            assert status["active_requests"] == 2
            assert status["waiting_requests"] == 1

        asyncio.run(scenario())

    def test_priority_queue(self):
        """優先度キューンのテスト"""

        async def scenario() -> None:
            manager = GPUResourceManager(max_concurrent=1)

            request1 = GPURequest(request_id="req1", process_id=1, model_name="model1", priority=1)
            await manager.acquire_gpu(request1)

            request2 = GPURequest(request_id="req2", process_id=2, model_name="model2", priority=10)
            await manager.acquire_gpu(request2)

            await manager.release_gpu("req1")

            status = await manager.get_status()
            assert status["active_requests"] == 1
            assert "req2" in status["active_request_ids"]

        asyncio.run(scenario())


def test_gpu_context():
    """GPUコンテキストマネージャーのテスト"""

    async def scenario() -> None:
        manager = GPUResourceManager(max_concurrent=1)

        request = GPURequest(
            request_id="req1",
            process_id=123,
            model_name="test-model",
        )

        async with GPUContext(manager, request) as ctx:
            assert ctx.acquired is True
            status = await manager.get_status()
            assert status["active_requests"] == 1

        status = await manager.get_status()
        assert status["active_requests"] == 0

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








