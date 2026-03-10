#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 ManaOS統合APIクライアント
全サービスへの統一的なAPI呼び出しを提供
"""

import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import lru_cache
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from intelligent_retry import IntelligentRetry

from _paths import (
    CONTENT_GENERATION_PORT,
    EXECUTOR_ENHANCED_PORT,
    FILE_SECRETARY_PORT,
    INTENT_ROUTER_PORT,
    LEARNING_SYSTEM_PORT,
    LLM_ROUTING_PORT,
    ORCHESTRATOR_PORT,
    PORTAL_INTEGRATION_PORT,
    RAG_MEMORY_PORT,
    TASK_CRITIC_PORT,
    TASK_PLANNER_PORT,
    TASK_QUEUE_PORT,
    MRL_MEMORY_PORT,
    SLACK_INTEGRATION_PORT,
)

# ロガーの初期化
logger = get_service_logger("manaos-unified-client")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedClient")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# リトライシステムの初期化
retry_system = IntelligentRetry()

DEFAULT_INTENT_ROUTER_URL = f"http://127.0.0.1:{INTENT_ROUTER_PORT}"
DEFAULT_TASK_PLANNER_URL = f"http://127.0.0.1:{TASK_PLANNER_PORT}"
DEFAULT_TASK_CRITIC_URL = f"http://127.0.0.1:{TASK_CRITIC_PORT}"
DEFAULT_RAG_MEMORY_URL = f"http://127.0.0.1:{RAG_MEMORY_PORT}"
DEFAULT_TASK_QUEUE_URL = f"http://127.0.0.1:{TASK_QUEUE_PORT}"
DEFAULT_UI_OPERATIONS_URL = f"http://127.0.0.1:{MRL_MEMORY_PORT}"
DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"
DEFAULT_EXECUTOR_ENHANCED_URL = f"http://127.0.0.1:{EXECUTOR_ENHANCED_PORT}"
DEFAULT_PORTAL_INTEGRATION_URL = f"http://127.0.0.1:{PORTAL_INTEGRATION_PORT}"
DEFAULT_CONTENT_GENERATION_URL = f"http://127.0.0.1:{CONTENT_GENERATION_PORT}"
DEFAULT_LLM_ROUTING_URL = f"http://127.0.0.1:{LLM_ROUTING_PORT}"
DEFAULT_SLACK_INTEGRATION_URL = f"http://127.0.0.1:{SLACK_INTEGRATION_PORT}"
DEFAULT_FILE_SECRETARY_URL = f"http://127.0.0.1:{FILE_SECRETARY_PORT}"
DEFAULT_LEARNING_SYSTEM_URL = f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}"


class UnifiedAPIClient:
    """統合APIクライアント"""
    
    def __init__(self):
        """初期化"""
        # サービス定義
        self.services = {
            "intent_router": {
                "url": os.getenv("INTENT_ROUTER_URL", DEFAULT_INTENT_ROUTER_URL),
                "port": INTENT_ROUTER_PORT,
            },
            "task_planner": {
                "url": os.getenv("TASK_PLANNER_URL", DEFAULT_TASK_PLANNER_URL),
                "port": TASK_PLANNER_PORT,
            },
            "task_critic": {
                "url": os.getenv("TASK_CRITIC_URL", DEFAULT_TASK_CRITIC_URL),
                "port": TASK_CRITIC_PORT,
            },
            "rag_memory": {
                "url": os.getenv("RAG_MEMORY_URL", DEFAULT_RAG_MEMORY_URL),
                "port": RAG_MEMORY_PORT,
            },
            "task_queue": {
                "url": os.getenv("TASK_QUEUE_URL", DEFAULT_TASK_QUEUE_URL),
                "port": TASK_QUEUE_PORT,
            },
            "ui_operations": {
                "url": os.getenv(
                    "UI_OPERATIONS_URL",
                    os.getenv("MRL_MEMORY_API_URL", DEFAULT_UI_OPERATIONS_URL),
                ),
                "port": MRL_MEMORY_PORT,
            },
            "unified_orchestrator": {
                "url": os.getenv("ORCHESTRATOR_URL", DEFAULT_ORCHESTRATOR_URL),
                "port": ORCHESTRATOR_PORT,
            },
            "executor_enhanced": {
                "url": os.getenv("EXECUTOR_ENHANCED_URL", DEFAULT_EXECUTOR_ENHANCED_URL),
                "port": EXECUTOR_ENHANCED_PORT,
            },
            "portal_integration": {
                "url": os.getenv(
                    "PORTAL_INTEGRATION_URL",
                    os.getenv("PORTAL_URL", DEFAULT_PORTAL_INTEGRATION_URL),
                ),
                "port": PORTAL_INTEGRATION_PORT,
            },
            "content_generation": {
                "url": os.getenv("CONTENT_GENERATION_URL", DEFAULT_CONTENT_GENERATION_URL),
                "port": CONTENT_GENERATION_PORT,
            },
            "llm_routing": {
                "url": os.getenv("LLM_ROUTING_URL", DEFAULT_LLM_ROUTING_URL),
                "port": LLM_ROUTING_PORT,
            },
            "service_monitor": {
                "url": os.getenv("SERVICE_MONITOR_URL", DEFAULT_LLM_ROUTING_URL),
                "port": LLM_ROUTING_PORT,
            },
            "slack_integration": {
                "url": os.getenv("SLACK_INTEGRATION_URL", DEFAULT_SLACK_INTEGRATION_URL),
                "port": SLACK_INTEGRATION_PORT,
            },
            "file_secretary": {
                "url": os.getenv("FILE_SECRETARY_URL", DEFAULT_FILE_SECRETARY_URL),
                "port": FILE_SECRETARY_PORT,
            },
            "learning_system": {
                "url": os.getenv("LEARNING_SYSTEM_URL", DEFAULT_LEARNING_SYSTEM_URL),
                "port": LEARNING_SYSTEM_PORT,
            },
        }
        
        # HTTPクライアント（接続プール使用）
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout_config.get("api_call", 10.0)),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        
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
            "retry_count": 0
        }
    
    def _get_cache_key(self, service: str, endpoint: str, params: Dict[str, Any]) -> str:
        """キャッシュキーを生成"""
        return f"{service}:{endpoint}:{json.dumps(params, sort_keys=True)}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """キャッシュが有効かチェック"""
        if not cache_entry:
            return False
        age = (datetime.now() - datetime.fromisoformat(cache_entry["timestamp"])).total_seconds()
        return age < self.cache_ttl
    
    def _clean_cache(self):
        """期限切れキャッシュを削除"""
        now = datetime.now()
        expired_keys = []
        for key, entry in self.cache.items():
            age = (now - datetime.fromisoformat(entry["timestamp"])).total_seconds()
            if age >= self.cache_ttl:
                expired_keys.append(key)
        for key in expired_keys:
            del self.cache[key]
    
    def call_service(
        self,
        service: str,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        retry: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        サービスを呼び出す
        
        Args:
            service: サービス名
            endpoint: エンドポイント
            method: HTTPメソッド
            data: リクエストボディ
            params: クエリパラメータ
            use_cache: キャッシュを使用するか
            retry: リトライするか
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
        
        # リトライロジック（簡易実装）
        if retry:
            max_retries = 3
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = self._make_request(url, method, data, params, timeout)
                    if result.get("status") != "error":
                        break
                    last_error = result
                    if attempt < max_retries:
                        import time
                        time.sleep(1.0 * (attempt + 1))  # 指数バックオフ
                except Exception as e:
                    last_error = {"error": str(e), "status": "error"}
                    if attempt < max_retries:
                        import time
                        time.sleep(1.0 * (attempt + 1))
            if last_error and result.get("status") == "error":  # type: ignore[possibly-unbound]
                result = last_error
                self.stats["retry_count"] += max_retries
        else:
            result = self._make_request(url, method, data, params, timeout)
        
        # エラーチェック
        if "error" in result:  # type: ignore[possibly-unbound]
            self.stats["failed_requests"] += 1
            return result  # type: ignore[possibly-unbound]
        
        # 成功
        self.stats["successful_requests"] += 1
        
        # キャッシュに保存（GETリクエストのみ）
        if use_cache and method.upper() == "GET":
            cache_key = self._get_cache_key(service, endpoint, params or {})
            self.cache[cache_key] = {
                "data": result,  # type: ignore[possibly-unbound]
                "timestamp": datetime.now().isoformat()
            }
            self._clean_cache()
        
        return result  # type: ignore[possibly-unbound]
    
    def _make_request(
        self,
        url: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """HTTPリクエストを実行"""
        try:
            request_timeout = timeout or timeout_config.get("api_call", 10.0)
            
            if method.upper() == "GET":
                response = self.client.get(url, params=params, timeout=request_timeout)
            elif method.upper() == "POST":
                response = self.client.post(url, json=data, params=params, timeout=request_timeout)
            elif method.upper() == "PUT":
                response = self.client.put(url, json=data, params=params, timeout=request_timeout)
            elif method.upper() == "DELETE":
                response = self.client.delete(url, params=params, timeout=request_timeout)
            else:
                raise ValueError(f"サポートされていないHTTPメソッド: {method}")
            
            response.raise_for_status()
            
            # JSONレスポンスを返す
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            else:
                return {"text": response.text, "status_code": response.status_code}
        
        except httpx.TimeoutException as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "method": method},
                user_message="リクエストがタイムアウトしました"
            )
            return {"error": error.user_message or error.message, "status": "timeout"}
        
        except httpx.HTTPStatusError as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "status_code": e.response.status_code},
                user_message=f"HTTPエラー: {e.response.status_code}"
            )
            return {"error": error.user_message or error.message, "status": "http_error", "status_code": e.response.status_code}
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"url": url, "method": method},
                user_message="リクエストの実行に失敗しました"
            )
            return {"error": error.user_message or error.message, "status": "error"}
    
    def call_multiple_services(
        self,
        calls: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        複数のサービスを呼び出す
        
        Args:
            calls: 呼び出し定義のリスト
            parallel: 並列実行するか
        
        Returns:
            結果のリスト
        """
        if parallel:
            return self._call_parallel(calls)
        else:
            return self._call_sequential(calls)
    
    def _call_sequential(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """順次実行"""
        results = []
        for call in calls:
            result = self.call_service(**call)
            results.append(result)
        return results
    
    def _call_parallel(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """asyncioを使用した並列実行"""

        async def _run_all() -> List[Dict[str, Any]]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_config.get("api_call", 10.0)),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            ) as async_client:
                tasks = [self._async_call(async_client, c) for c in calls]
                return list(await asyncio.gather(*tasks, return_exceptions=False))

        try:
            return asyncio.run(_run_all())
        except RuntimeError:
            # イベントループが既に実行中の場合は順次実行にフォールバック
            logger.debug("イベントループ実行中のためsequentialにフォールバック")
            return self._call_sequential(calls)

    async def _async_call(
        self,
        client: httpx.AsyncClient,
        call: Dict[str, Any],
    ) -> Dict[str, Any]:
        """単一の非同期API呼び出し"""
        service = call.get("service", "")
        endpoint = call.get("endpoint", "/")
        method = call.get("method", "GET").upper()
        data = call.get("data")
        params = call.get("params")
        timeout = call.get("timeout")

        service_info = self.services.get(service)
        if not service_info:
            return {"error": f"不明なサービス: {service}", "status": "error"}

        url = f"{service_info['url']}{endpoint}"
        req_timeout = timeout or timeout_config.get("api_call", 10.0)

        try:
            if method == "GET":
                resp = await client.get(url, params=params, timeout=req_timeout)
            elif method == "POST":
                resp = await client.post(url, json=data, params=params, timeout=req_timeout)
            elif method == "PUT":
                resp = await client.put(url, json=data, params=params, timeout=req_timeout)
            elif method == "DELETE":
                resp = await client.delete(url, params=params, timeout=req_timeout)
            else:
                return {"error": f"サポートされていないHTTPメソッド: {method}", "status": "error"}

            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            return {"text": resp.text, "status_code": resp.status_code}
        except Exception as e:
            logger.warning(f"並列呼び出し失敗 ({service}{endpoint}): {e}")
            return {"error": str(e), "status": "error"}
    
    def check_service_health(self, service: str) -> Dict[str, Any]:
        """サービスのヘルスチェック"""
        return self.call_service(
            service=service,
            endpoint="/health",
            method="GET",
            use_cache=True,
            timeout=5.0
        )
    
    def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """全サービスのヘルスチェック"""
        results = {}
        for service in self.services.keys():
            results[service] = self.check_service_health(service)
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "services_count": len(self.services),
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            ) * 100
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.cache.clear()
        logger.info("キャッシュをクリアしました")
    
    def close(self):
        """クライアントを閉じる"""
        self.client.close()


# グローバルインスタンス
_unified_client: Optional[UnifiedAPIClient] = None


def get_unified_client() -> UnifiedAPIClient:
    """統合APIクライアントのシングルトンインスタンスを取得"""
    global _unified_client
    if _unified_client is None:
        _unified_client = UnifiedAPIClient()
    return _unified_client


def main():
    """テスト用メイン関数"""
    print("ManaOS統合APIクライアントテスト")
    print("=" * 60)
    
    client = get_unified_client()
    
    # 全サービスのヘルスチェック
    print("\n全サービスのヘルスチェック中...")
    health_results = client.check_all_services()
    
    print("\n結果:")
    for service, result in health_results.items():
        status = "✅" if result.get("status") == "healthy" else "❌"
        print(f"{status} {service}: {result.get('status', 'unknown')}")
    
    # 統計情報
    print("\n統計情報:")
    stats = client.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    client.close()


if __name__ == "__main__":
    main()

