#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 GPU並列実行システム
複数のLLMリクエストをGPUで並列処理
"""

import asyncio
import time
from manaos_logger import get_logger
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import os
import requests

try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

logger = get_service_logger("gpu-parallel-executor")


@dataclass


class ParallelRequest:
    """並列リクエスト"""
    request_id: str
    model: str
    prompt: str
    task_type: str
    priority: int = 5
    callback: Optional[Callable] = None


class GPUParallelExecutor:
    """GPU並列実行システム"""
    
    def __init__(self, max_parallel: int = 4):
        """
        初期化
        
        Args:
            max_parallel: 最大並列実行数
        """
        self.max_parallel = max_parallel
        self.semaphore = asyncio.Semaphore(max_parallel)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[Dict[str, Any]] = []
        
        self.ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
    
    async def execute_parallel(
        self,
        requests: List[ParallelRequest],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        複数のリクエストを並列実行
        
        Args:
            requests: リクエストリスト
            timeout: タイムアウト（秒）
            
        Returns:
            結果リスト
        """
        start_time = time.time()
        
        # 優先度順にソート
        sorted_requests = sorted(requests, key=lambda r: r.priority, reverse=True)
        
        # 並列実行
        tasks = [self._execute_with_semaphore(req) for req in sorted_requests]
        
        try:
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 並列実行がタイムアウトしました（{timeout}秒）")
            results = [{"error": "timeout"} for _ in requests]
        
        elapsed = time.time() - start_time
        
        # 結果を整形
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "request_id": sorted_requests[i].request_id,
                    "error": str(result),
                    "success": False
                })
            else:
                formatted_results.append({
                    "request_id": sorted_requests[i].request_id,
                    "result": result,
                    "success": True,
                    "elapsed_time": elapsed
                })
        
        logger.info(f"✅ 並列実行完了: {len(requests)}件を{elapsed:.2f}秒で処理")
        
        return formatted_results
    
    async def _execute_with_semaphore(self, request: ParallelRequest) -> Dict[str, Any]:
        """セマフォを使用して実行"""
        async with self.semaphore:
            return await self._execute_llm_call(request)
    
    async def _execute_llm_call(self, request: ParallelRequest) -> Dict[str, Any]:
        """LLM呼び出しを実行"""
        # 非同期HTTPリクエスト（httpx使用）
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": request.model,
                        "messages": [{"role": "user", "content": request.prompt}],
                        "stream": False,
                        "options": {
                            "num_gpu": 99,  # GPUを最大限使用
                            "num_thread": 8
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # コールバックを実行
                    if request.callback:
                        await request.callback(result)
                    
                    return result
                else:
                    raise Exception(f"Ollama APIエラー: {response.status_code}")
        except ImportError:
            # httpxが利用できない場合、同期リクエスト
            logger.warning("httpxが利用できないため、同期リクエストを使用します")
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "stream": False,
                    "options": {
                        "num_gpu": 99,
                        "num_thread": 8
                    }
                },
                timeout=300
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Ollama APIエラー: {response.status_code}")
    
    async def execute_streaming_parallel(
        self,
        requests: List[ParallelRequest],
        callback: Optional[Callable] = None
    ):
        """ストリーミング並列実行"""
        tasks = []
        for req in requests:
            task = self._execute_streaming(req, callback)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_streaming(
        self,
        request: ParallelRequest,
        callback: Optional[Callable] = None
    ):
        """ストリーミング実行"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": request.model,
                        "messages": [{"role": "user", "content": request.prompt}],
                        "stream": True,
                        "options": {
                            "num_gpu": 99,
                            "num_thread": 8
                        }
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                if callback:
                                    await callback(request.request_id, data)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"ストリーミング実行エラー: {e}")


# シングルトンインスタンス
_parallel_executor: Optional[GPUParallelExecutor] = None


def get_parallel_executor(max_parallel: int = 4) -> GPUParallelExecutor:
    """並列実行システムのシングルトン取得"""
    global _parallel_executor
    if _parallel_executor is None:
        _parallel_executor = GPUParallelExecutor(max_parallel=max_parallel)
    return _parallel_executor

