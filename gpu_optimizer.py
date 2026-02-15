#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ GPU最適化システム
GPUを最大限活用して処理速度を向上
"""

import asyncio
import os
import time
from manaos_logger import get_logger
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import subprocess
import platform

try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

logger = get_service_logger("gpu-optimizer")


@dataclass


class GPUOptimizationConfig:
    """GPU最適化設定"""
    max_concurrent_requests: int = 4  # 同時実行数を増やす（デフォルト2→4）
    enable_batch_processing: bool = True  # バッチ処理を有効化
    enable_model_preloading: bool = True  # モデルの事前ロード
    enable_pipeline_processing: bool = True  # パイプライン処理
    batch_size: int = 4  # バッチサイズ
    preload_models: List[str] = field(default_factory=lambda: [
        "qwen2.5:7b",
        "qwen2.5:14b",
        "llama3.2:3b"
    ])


class GPUOptimizer:
    """GPU最適化システム"""
    
    def __init__(self, config: Optional[GPUOptimizationConfig] = None):
        """
        初期化
        
        Args:
            config: 最適化設定
        """
        self.config = config or GPUOptimizationConfig()
        self.gpu_manager = None
        self.preloaded_models: Dict[str, bool] = {}
        self.batch_queue: deque = deque()
        self.processing_batch = False
        
        # GPU使用統計
        self.stats = {
            "total_requests": 0,
            "gpu_requests": 0,
            "cpu_requests": 0,
            "batch_processed": 0,
            "average_gpu_utilization": 0.0,
            "total_time_saved": 0.0  # 秒
        }
    
    async def initialize(self):
        """初期化（GPUマネージャーとモデルの事前ロード）"""
        try:
            from gpu_resource_manager import get_gpu_manager
            
            # GPUマネージャーを初期化（同時実行数を増やす）
            self.gpu_manager = get_gpu_manager(max_concurrent=self.config.max_concurrent_requests)
            await self.gpu_manager.start_monitoring()
            
            # モデルの事前ロード
            if self.config.enable_model_preloading:
                await self._preload_models()
            
            logger.info("✅ GPU最適化システムを初期化しました")
        except Exception as e:
            logger.error(f"GPU最適化システムの初期化エラー: {e}")
    
    async def _preload_models(self):
        """モデルを事前ロード（GPUメモリに常駐）"""
        import requests
        
        ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        
        for model in self.config.preload_models:
            try:
                # モデルをロード（実際の推論はしない）
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": "test",
                        "stream": False,
                        "options": {
                            "num_gpu": 99,
                            "num_predict": 1  # 最小限の推論
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.preloaded_models[model] = True
                    logger.info(f"✅ モデルを事前ロード: {model}")
                else:
                    logger.warning(f"⚠️ モデルの事前ロード失敗: {model}")
            except Exception as e:
                logger.warning(f"⚠️ モデルの事前ロードエラー ({model}): {e}")
    
    async def optimize_llm_call(
        self,
        model: str,
        prompt: str,
        task_type: str = "conversation",
        use_batch: bool = True
    ) -> Dict[str, Any]:
        """
        LLM呼び出しを最適化
        
        Args:
            model: モデル名
            prompt: プロンプト
            task_type: タスクタイプ
            use_batch: バッチ処理を使用するか
            
        Returns:
            最適化された結果
        """
        self.stats["total_requests"] += 1
        
        # バッチ処理が有効で、キューに他のリクエストがある場合
        if use_batch and self.config.enable_batch_processing and len(self.batch_queue) > 0:
            return await self._process_batch(model, prompt, task_type)
        
        # 通常の最適化処理
        return await self._process_optimized(model, prompt, task_type)
    
    async def _process_optimized(
        self,
        model: str,
        prompt: str,
        task_type: str
    ) -> Dict[str, Any]:
        """最適化された処理"""
        from gpu_resource_manager import GPURequest
        import uuid
        
        request_id = str(uuid.uuid4())
        request = GPURequest(
            request_id=request_id,
            process_id=os.getpid(),
            model_name=model,
            priority=10 if task_type == "reasoning" else 5,
            estimated_duration=60
        )
        
        # GPUリソースを取得
        acquired = await self.gpu_manager.acquire_gpu(request)
        
        if not acquired:
            # GPUが取得できない場合、バッチキューに追加
            if self.config.enable_batch_processing:
                self.batch_queue.append({
                    "model": model,
                    "prompt": prompt,
                    "task_type": task_type,
                    "request_id": request_id
                })
                return {"status": "queued", "request_id": request_id}
            else:
                # CPUモードで実行
                return await self._fallback_cpu(model, prompt, task_type)
        
        try:
            # GPUで実行
            start_time = time.time()
            result = await self._execute_gpu_call(model, prompt, task_type)
            elapsed = time.time() - start_time
            
            self.stats["gpu_requests"] += 1
            self.stats["total_time_saved"] += elapsed * 0.7  # GPUはCPUより約3倍速いと仮定
            
            return {
                "status": "success",
                "result": result,
                "gpu_mode": True,
                "elapsed_time": elapsed,
                "request_id": request_id
            }
        finally:
            await self.gpu_manager.release_gpu(request_id)
    
    async def _process_batch(
        self,
        model: str,
        prompt: str,
        task_type: str
    ) -> Dict[str, Any]:
        """バッチ処理"""
        # バッチキューに追加
        import uuid
        request_id = str(uuid.uuid4())
        
        self.batch_queue.append({
            "model": model,
            "prompt": prompt,
            "task_type": task_type,
            "request_id": request_id
        })
        
        # バッチ処理が実行中でない場合、開始
        if not self.processing_batch:
            asyncio.create_task(self._execute_batch())
        
        return {"status": "queued_for_batch", "request_id": request_id}
    
    async def _execute_batch(self):
        """バッチを実行"""
        if self.processing_batch or len(self.batch_queue) == 0:
            return
        
        self.processing_batch = True
        
        try:
            # バッチサイズ分のリクエストを取得
            batch = []
            while len(batch) < self.config.batch_size and len(self.batch_queue) > 0:
                batch.append(self.batch_queue.popleft())
            
            if not batch:
                return
            
            # 同じモデルのリクエストをグループ化
            model_groups = {}
            for req in batch:
                model = req["model"]
                if model not in model_groups:
                    model_groups[model] = []
                model_groups[model].append(req)
            
            # 各モデルグループを並列処理
            tasks = []
            for model, requests in model_groups.items():
                task = self._process_model_batch(model, requests)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            self.stats["batch_processed"] += len(batch)
            logger.info(f"✅ バッチ処理完了: {len(batch)}件を処理")
            
        finally:
            self.processing_batch = False
            
            # キューに残っているリクエストがあれば再実行
            if len(self.batch_queue) > 0:
                await self._execute_batch()
    
    async def _process_model_batch(self, model: str, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """モデルごとのバッチ処理"""
        from gpu_resource_manager import GPURequest
        import uuid
        
        request_id = f"batch_{uuid.uuid4()}"
        request = GPURequest(
            request_id=request_id,
            process_id=os.getpid(),
            model_name=model,
            priority=8,
            estimated_duration=len(requests) * 30
        )
        
        acquired = await self.gpu_manager.acquire_gpu(request)
        if not acquired:
            # GPUが取得できない場合、個別に処理
            return await self._process_individually(requests)
        
        try:
            # バッチで処理（複数のプロンプトをまとめて）
            prompts = [req["prompt"] for req in requests]
            results = await self._execute_gpu_batch(model, prompts)
            
            # 結果を各リクエストに割り当て
            formatted_results = []
            for i, req in enumerate(requests):
                formatted_results.append({
                    "request_id": req["request_id"],
                    "result": results[i] if i < len(results) else None,
                    "gpu_mode": True,
                    "batch_processed": True
                })
            
            return formatted_results
        finally:
            await self.gpu_manager.release_gpu(request_id)
    
    async def _execute_gpu_call(self, model: str, prompt: str, task_type: str) -> Dict[str, Any]:
        """GPUでLLM呼び出しを実行"""
        import requests
        
        ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        
        # GPUを最大限使用
        response = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "num_gpu": 99,  # GPUを最大限使用
                    "num_thread": 8  # CPUスレッド数も最適化
                }
            },
            timeout=300
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ollama APIエラー: {response.status_code}")
    
    async def _execute_gpu_batch(self, model: str, prompts: List[str]) -> List[Dict[str, Any]]:
        """GPUでバッチ処理を実行"""
        import requests
        
        ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        
        # 複数のプロンプトを並列処理
        tasks = []
        for prompt in prompts:
            task = self._execute_gpu_call(model, prompt, "batch")
            tasks.append(task)
        
        # 並列実行（GPUが複数のリクエストを同時処理できる場合）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _process_individually(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """個別に処理（フォールバック）"""
        results = []
        for req in requests:
            try:
                result = await self._process_optimized(
                    req["model"],
                    req["prompt"],
                    req["task_type"]
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "request_id": req["request_id"],
                    "error": str(e)
                })
        return results
    
    async def _fallback_cpu(self, model: str, prompt: str, task_type: str) -> Dict[str, Any]:
        """CPUモードでフォールバック"""
        import requests
        
        ollama_url = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        
        response = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "num_gpu": 0  # CPUモード
                }
            },
            timeout=300
        )
        
        self.stats["cpu_requests"] += 1
        
        if response.status_code == 200:
            return {
                "status": "success",
                "result": response.json(),
                "gpu_mode": False
            }
        else:
            raise Exception(f"Ollama APIエラー: {response.status_code}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """最適化統計を取得"""
        gpu_utilization = self._get_gpu_utilization()
        
        return {
            **self.stats,
            "current_gpu_utilization": gpu_utilization,
            "batch_queue_size": len(self.batch_queue),
            "preloaded_models": list(self.preloaded_models.keys()),
            "optimization_rate": (
                self.stats["gpu_requests"] / max(self.stats["total_requests"], 1)
            ) * 100
        }
    
    def _get_gpu_utilization(self) -> float:
        """GPU使用率を取得"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return float(result.stdout.strip())
        except Exception:
            pass
        return 0.0


# シングルトンインスタンス
_gpu_optimizer: Optional[GPUOptimizer] = None


def get_gpu_optimizer(config: Optional[GPUOptimizationConfig] = None) -> GPUOptimizer:
    """GPU最適化システムのシングルトン取得"""
    global _gpu_optimizer
    if _gpu_optimizer is None:
        _gpu_optimizer = GPUOptimizer(config=config)
    return _gpu_optimizer

