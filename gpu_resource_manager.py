#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 GPUリソース管理システム
GPUリソースの競合を防ぎ、効率的に使用
"""

import asyncio
import time
from manaos_logger import get_logger
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import psutil
import subprocess
import platform

logger = get_logger(__name__)


class GPUStatus(Enum):
    """GPUステータス"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    ERROR = "error"


@dataclass


class GPURequest:
    """GPUリクエスト"""
    request_id: str
    process_id: int
    model_name: str
    priority: int = 5  # 1-10, 10が最高優先度
    requested_at: datetime = field(default_factory=datetime.now)
    timeout: int = 300  # 秒
    estimated_duration: int = 60  # 秒


class GPUResourceManager:
    """GPUリソース管理"""
    
    def __init__(self, max_concurrent: int = 2):
        """
        初期化
        
        Args:
            max_concurrent: 同時実行可能なプロセス数
        """
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue(maxsize=max_concurrent * 2)
        self.active_requests: Dict[str, GPURequest] = {}
        self.waiting_queue: List[GPURequest] = []
        self.gpu_status = GPUStatus.AVAILABLE
        self.lock = asyncio.Lock()
        
        # GPU使用状況の監視
        self.monitoring = False
        self.monitor_task = None
    
    async def acquire_gpu(self, request: GPURequest) -> bool:
        """
        GPUリソースを取得
        
        Args:
            request: GPUリクエスト
            
        Returns:
            取得成功したかどうか
        """
        async with self.lock:
            # アクティブなリクエスト数をチェック
            if len(self.active_requests) < self.max_concurrent:
                self.active_requests[request.request_id] = request
                self.gpu_status = GPUStatus.IN_USE
                logger.info(f"✅ GPUリソースを取得: {request.request_id} ({request.model_name})")
                return True
            else:
                # キューに追加
                self.waiting_queue.append(request)
                self.waiting_queue.sort(key=lambda x: x.priority, reverse=True)
                logger.info(f"⏳ GPUリソース待機中: {request.request_id} (優先度: {request.priority})")
                return False
    
    async def release_gpu(self, request_id: str) -> None:
        """
        GPUリソースを解放
        
        Args:
            request_id: リクエストID
        """
        async with self.lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
                logger.info(f"✅ GPUリソースを解放: {request_id}")
            
            # 待機中のリクエストを処理
            if self.waiting_queue and len(self.active_requests) < self.max_concurrent:
                next_request = self.waiting_queue.pop(0)
                self.active_requests[next_request.request_id] = next_request
                logger.info(f"✅ 待機中のリクエストを開始: {next_request.request_id}")
                # イベントを通知（必要に応じて）
                await self.queue.put(next_request)
            
            # アクティブなリクエストがない場合
            if not self.active_requests:
                self.gpu_status = GPUStatus.AVAILABLE
    
    async def get_status(self) -> Dict[str, Any]:
        """ステータスを取得"""
        async with self.lock:
            return {
                "status": self.gpu_status.value,
                "active_requests": len(self.active_requests),
                "waiting_requests": len(self.waiting_queue),
                "max_concurrent": self.max_concurrent,
                "active_request_ids": list(self.active_requests.keys()),
                "waiting_request_ids": [r.request_id for r in self.waiting_queue]
            }
    
    async def cleanup_stale_requests(self) -> None:
        """古いリクエストをクリーンアップ"""
        async with self.lock:
            now = datetime.now()
            stale_requests = []
            
            for request_id, request in self.active_requests.items():
                elapsed = (now - request.requested_at).total_seconds()
                if elapsed > request.timeout:
                    stale_requests.append(request_id)
            
            for request_id in stale_requests:
                logger.warning(f"⚠️ タイムアウトしたリクエストをクリーンアップ: {request_id}")
                await self.release_gpu(request_id)
    
    async def start_monitoring(self, interval: int = 30) -> None:
        """GPU使用状況の監視を開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        async def monitor():
            while self.monitoring:
                try:
                    await self.cleanup_stale_requests()
                    await self._check_gpu_usage()
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"監視エラー: {e}")
        
        self.monitor_task = asyncio.create_task(monitor())
        logger.info("✅ GPU監視を開始しました")
    
    async def stop_monitoring(self) -> None:
        """GPU使用状況の監視を停止"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ GPU監視を停止しました")
    
    async def _check_gpu_usage(self):
        """GPU使用状況をチェック"""
        try:
            # Ollamaプロセスをチェック
            ollama_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'serve' in cmdline or 'run' in cmdline:
                            ollama_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # アクティブなリクエストとプロセス数を比較
            if len(ollama_processes) > self.max_concurrent:
                logger.warning(
                    f"⚠️ GPU使用プロセス数が上限を超えています: "
                    f"{len(ollama_processes)}/{self.max_concurrent}"
                )
        except Exception as e:
            logger.error(f"GPU使用状況チェックエラー: {e}")
    
    def get_gpu_memory_usage(self) -> Optional[float]:
        """GPUメモリ使用率を取得（nvidia-smi使用）"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        used, total = map(int, lines[0].split(','))
                        return used / total * 100
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return None


# コンテキストマネージャー


class GPUContext:
    """GPUリソースのコンテキストマネージャー"""
    
    def __init__(self, manager: GPUResourceManager, request: GPURequest):
        self.manager = manager
        self.request = request
        self.acquired = False
    
    async def __aenter__(self):
        self.acquired = await self.manager.acquire_gpu(self.request)
        if not self.acquired:
            # 待機（簡易実装）
            while not self.acquired:
                await asyncio.sleep(1)
                self.acquired = await self.manager.acquire_gpu(self.request)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            await self.manager.release_gpu(self.request.request_id)


# シングルトンインスタンス
_gpu_manager: Optional[GPUResourceManager] = None


def get_gpu_manager(max_concurrent: int = 2) -> GPUResourceManager:
    """GPUマネージャーのシングルトン取得"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUResourceManager(max_concurrent=max_concurrent)
    return _gpu_manager

