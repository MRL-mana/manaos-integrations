#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 ManaOS非同期統合APIクライアント
真の並列処理を実装した高性能版
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import lru_cache

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("AsyncUnifiedClient")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


class AsyncUnifiedAPIClient:
    """非同期統合APIクライアント（高性能版）"""
    
    def __init__(self):
        """初期化"""
        # サービス定義
        self.services = {
            "intent_router": {"url": "http://127.0.0.1:5100", "port": 5100},
            "task_planner": {"url": "http://127.0.0.1:5101", "port": 5101},
            "task_critic": {"url": "http://127.0.0.1:5102", "port": 5102},
            "rag_memory": {"url": "http://127.0.0.1:5103", "port": 5103},
            "task_queue": {"url": "http://127.0.0.1:5104", "port": 5104},
            "ui_operations": {"url": "http://127.0.0.1:5105", "port": 5105},
            "unified_orchestrator": {"url": "http://127.0.0.1:5106", "port": 5106},
            "executor_enhanced": {"url": "http://127.0.0.1:5107", "port": 5107},
            "portal_integration": {"url": "http://127.0.0.1:5108", "port": 5108},
            "content_generation": {"url": "http://127.0.0.1:5109", "port": 5109},
            "llm_routing": {"url": "http://127.0.0.1:5111", "port": 5111},
            "service_monitor": {"url": "http://127.0.0.1:5111", "port": 5111},
            "slack_integration": {"url": "http://127.0.0.1:5114", "port": 5114},
            "file_secretary": {"url": "http://127.0.0.1:5120", "port": 5120},
            "learning_system": {"url": "http://127.0.0.1:5126", "port": 5126},
        }
        
        # 非同期HTTPクライアント（接続プール使用）
        self.client: Optional[httpx.AsyncClient] = None
        
        # キャッシュ（簡易実装）
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 60  # 60秒
        
        # 統計情報
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_calls": 0
        }
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        timeout = timeout_config.get("api_call", 10.0)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=200)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        if self.client:
            await self.client.aclose()
    
    def _get_cache_key(self, service: str, endpoint: str, params: Dict[str, Any]) -> str:
        """キャッシュキーを生成"""
        return f"{service}:{endpoint}:{json.dumps(params, sort_keys=True)}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """キャッシュが有効かチェック"""
        if not cache_entry:
            return False
        age = (datetime.now() - datetime.fromisoformat(cache_entry["timestamp"])).total_seconds()
        return age < self.cache_ttl
    
    async def call_service(
        self,
        service: str,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        サービスを呼び出す（非同期）
        
        Args:
            service: サービス名
            endpoint: エンドポイント
            method: HTTPメソッド
            data: リクエストボディ
            params: クエリパラメータ
            use_cache: キャッシュを使用するか
            timeout: タイムアウト（秒）
        
        Returns:
            レスポンスデータ
        """
        self.stats["total_requests"] += 1
        
        # サービスURLを取得
        if service not in self.services:
            error = error_handler.handle_exception(
                Exception(f"不明なサービス: {service}"),
                context={"service": service, "endpoint": endpoint},
                user_message=f"サービス '{service}' が見つかりません"
            )
            self.stats["failed_requests"] += 1
            return {"error": error.user_message or error.message, "status": "error"}
        
        service_url = self.services[service]["url"]
        url = f"{service_url}{endpoint}"
        
        # キャッシュチェック（GETリクエストのみ）
        if use_cache and method.upper() == "GET":
            cache_key = self._get_cache_key(service, endpoint, params or {})
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    self.stats["cache_hits"] += 1
                    logger.debug(f"キャッシュヒット: {service}:{endpoint}")
                    return cache_entry["data"]
            self.stats["cache_misses"] += 1
        
        # 非同期HTTPリクエスト
        try:
            request_timeout = timeout or timeout_config.get("api_call", 10.0)
            
            if method.upper() == "GET":
                response = await self.client.get(url, params=params, timeout=request_timeout)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data, params=params, timeout=request_timeout)
            elif method.upper() == "PUT":
                response = await self.client.put(url, json=data, params=params, timeout=request_timeout)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, params=params, timeout=request_timeout)
            else:
                raise ValueError(f"サポートされていないHTTPメソッド: {method}")
            
            response.raise_for_status()
            
            # JSONレスポンスを返す
            if response.headers.get("content-type", "").startswith("application/json"):
                result = response.json()
            else:
                result = {"text": response.text, "status_code": response.status_code}
            
            # 成功
            self.stats["successful_requests"] += 1
            
            # キャッシュに保存（GETリクエストのみ）
            if use_cache and method.upper() == "GET":
                cache_key = self._get_cache_key(service, endpoint, params or {})
                self.cache[cache_key] = {
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            
            return result
        
        except httpx.TimeoutException as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "method": method},
                user_message="リクエストがタイムアウトしました"
            )
            self.stats["failed_requests"] += 1
            return {"error": error.user_message or error.message, "status": "timeout"}
        
        except httpx.HTTPStatusError as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "status_code": e.response.status_code},
                user_message=f"HTTPエラー: {e.response.status_code}"
            )
            self.stats["failed_requests"] += 1
            return {"error": error.user_message or error.message, "status": "http_error", "status_code": e.response.status_code}
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "method": method},
                user_message="リクエストの実行に失敗しました"
            )
            self.stats["failed_requests"] += 1
            return {"error": error.user_message or error.message, "status": "error"}
    
    async def call_multiple_services(
        self,
        calls: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        複数のサービスを並列呼び出す（真の並列処理）
        
        Args:
            calls: 呼び出し定義のリスト
            max_concurrent: 最大同時実行数
        
        Returns:
            結果のリスト
        """
        self.stats["parallel_calls"] += len(calls)
        
        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def call_with_semaphore(call):
            async with semaphore:
                return await self.call_service(**call)
        
        # 並列実行
        tasks = [call_with_semaphore(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外をエラー結果に変換
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error = error_handler.handle_exception(
                    result,
                    context={"call": calls[i]},
                    user_message="サービス呼び出しに失敗しました"
                )
                formatted_results.append({
                    "error": error.user_message or error.message,
                    "status": "error"
                })
            else:
                formatted_results.append(result)
        
        return formatted_results
    
    async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """全サービスのヘルスチェック（並列実行）"""
        calls = [
            {
                "service": service,
                "endpoint": "/health",
                "method": "GET",
                "use_cache": True,
                "timeout": 5.0
            }
            for service in self.services.keys()
        ]
        
        results = await self.call_multiple_services(calls, max_concurrent=15)
        
        return {
            service: results[i]
            for i, service in enumerate(self.services.keys())
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "services_count": len(self.services),
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            ) * 100,
            "cache_hit_rate": (
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
            ) * 100
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.cache.clear()
        logger.info("キャッシュをクリアしました")


async def main():
    """テスト用メイン関数"""
    print("ManaOS非同期統合APIクライアントテスト")
    print("=" * 60)
    
    async with AsyncUnifiedAPIClient() as client:
        # 全サービスのヘルスチェック（並列実行）
        print("\n全サービスのヘルスチェック中（並列実行）...")
        import time
        start_time = time.time()
        health_results = await client.check_all_services()
        elapsed_time = time.time() - start_time
        
        print(f"\n結果（実行時間: {elapsed_time:.2f}秒）:")
        for service, result in health_results.items():
            status = "✅" if result.get("status") == "healthy" else "❌"
            print(f"{status} {service}: {result.get('status', 'unknown')}")
        
        # 統計情報
        print("\n統計情報:")
        stats = client.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())






















