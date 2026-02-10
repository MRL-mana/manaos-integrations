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
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from intelligent_retry import IntelligentRetry

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedClient")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# リトライシステムの初期化
retry_system = IntelligentRetry()


class UnifiedAPIClient:
    """統合APIクライアント"""
    
    def __init__(self):
        """初期化"""
        # サービス定義
        self.services = {
            "intent_router": {"url": "http://localhost:5100", "port": 5100},
            "task_planner": {"url": "http://localhost:5101", "port": 5101},
            "task_critic": {"url": "http://localhost:5102", "port": 5102},
            "rag_memory": {"url": "http://localhost:5103", "port": 5103},
            "task_queue": {"url": "http://localhost:5104", "port": 5104},
            "ui_operations": {"url": "http://localhost:5105", "port": 5105},
            "unified_orchestrator": {"url": "http://localhost:5106", "port": 5106},
            "executor_enhanced": {"url": "http://localhost:5107", "port": 5107},
            "portal_integration": {"url": "http://localhost:5108", "port": 5108},
            "content_generation": {"url": "http://localhost:5109", "port": 5109},
            "llm_optimization": {"url": "http://localhost:5110", "port": 5110},
            "service_monitor": {"url": "http://localhost:5111", "port": 5111},
            "slack_integration": {"url": "http://localhost:5114", "port": 5114},
            "file_secretary": {"url": "http://localhost:5120", "port": 5120},
            "learning_system": {"url": "http://localhost:5126", "port": 5126},
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
            if last_error and result.get("status") == "error":
                result = last_error
                self.stats["retry_count"] += max_retries
        else:
            result = self._make_request(url, method, data, params, timeout)
        
        # エラーチェック
        if "error" in result:
            self.stats["failed_requests"] += 1
            return result
        
        # 成功
        self.stats["successful_requests"] += 1
        
        # キャッシュに保存（GETリクエストのみ）
        if use_cache and method.upper() == "GET":
            cache_key = self._get_cache_key(service, endpoint, params or {})
            self.cache[cache_key] = {
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            self._clean_cache()
        
        return result
    
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

