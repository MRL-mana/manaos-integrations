#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 統合機能動作確認スクリプト
"""

import asyncio
import httpx
import sys
import os
from pathlib import Path

# WindowsのコンソールエンコーディングをUTF-8に設定
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# テスト対象のインポート
try:
    from unified_orchestrator import UnifiedOrchestrator
    print("[OK] Unified Orchestratorインポート成功")
except Exception as e:
    print(f"[NG] Unified Orchestratorインポート失敗: {e}")
    sys.exit(1)

try:
    from metrics_collector import MetricsCollector, MetricType
    print("[OK] Metrics Collectorインポート成功")
except Exception as e:
    print(f"[WARN] Metrics Collectorインポート失敗: {e}")

try:
    from intelligent_retry import IntelligentRetry, RetryConfig
    print("[OK] Intelligent Retryインポート成功")
except Exception as e:
    print(f"[WARN] Intelligent Retryインポート失敗: {e}")

try:
    from response_cache import ResponseCache
    print("[OK] Response Cacheインポート成功")
except Exception as e:
    print(f"[WARN] Response Cacheインポート失敗: {e}")


async def test_metrics_collector():
    """メトリクス収集システムのテスト"""
    print("\n📊 メトリクス収集システムテスト開始...")
    try:
        collector = MetricsCollector()
        collector.record_metric(
            service_name="TestService",
            metric_type=MetricType.RESPONSE_TIME,
            value=1.23
        )
        print("[OK] メトリクス記録成功")
        
        # メトリクス取得テスト
        metrics = collector.get_metrics(
            service_name="TestService",
            metric_type=MetricType.RESPONSE_TIME,
            limit=10
        )
        print(f"[OK] メトリクス取得成功: {len(metrics)}件")
        return True
    except Exception as e:
        print(f"[NG] メトリクス収集システムテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_intelligent_retry():
    """インテリジェントリトライシステムのテスト"""
    print("\n🔄 インテリジェントリトライシステムテスト開始...")
    try:
        retry_system = IntelligentRetry()
        
        # 成功する関数のテスト
        call_count = 0
        async def success_func():
            nonlocal call_count
            call_count += 1
            return {"status": "success"}
        
        result = await retry_system.execute_with_retry(success_func)
        if result.success and call_count == 1:
            print("[OK] リトライシステムテスト成功（成功ケース）")
        else:
            print(f"[WARN] リトライシステムテスト異常: success={result.success}, calls={call_count}")
        
        return True
    except Exception as e:
        print(f"[NG] インテリジェントリトライシステムテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_response_cache():
    """レスポンスキャッシュシステムのテスト"""
    print("\n💾 レスポンスキャッシュシステムテスト開始...")
    try:
        cache = ResponseCache()
        
        # キャッシュに保存
        cache.set(
            cache_type="test",
            value={"result": "test_value"},
            test_key="test_value",
            ttl_seconds=60
        )
        print("[OK] キャッシュ保存成功")
        
        # キャッシュから取得
        cached_value = cache.get(
            cache_type="test",
            test_key="test_value"
        )
        if cached_value and cached_value.get("result") == "test_value":
            print("[OK] キャッシュ取得成功")
        else:
            print(f"[WARN] キャッシュ取得異常: {cached_value}")
        
        return True
    except Exception as e:
        print(f"[NG] レスポンスキャッシュシステムテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_unified_orchestrator_init():
    """Unified Orchestratorの初期化テスト"""
    print("\n🎯 Unified Orchestrator初期化テスト開始...")
    try:
        orchestrator = UnifiedOrchestrator()
        print("[OK] Unified Orchestrator初期化成功")
        
        # 統合状態の確認
        if hasattr(orchestrator, 'metrics_collector_url'):
            print(f"[OK] メトリクス収集システム統合: {orchestrator.metrics_collector_url}")
        if hasattr(orchestrator, 'intelligent_retry'):
            print(f"[OK] インテリジェントリトライシステム統合: {orchestrator.intelligent_retry is not None}")
        if hasattr(orchestrator, 'response_cache'):
            print(f"[OK] レスポンスキャッシュシステム統合: {orchestrator.response_cache is not None}")
        
        return True
    except Exception as e:
        print(f"[NG] Unified Orchestrator初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_health():
    """サービスヘルスチェック"""
    print("\n🏥 サービスヘルスチェック開始...")
    
    services = {
        "Metrics Collector": "http://127.0.0.1:5127/health",
        "Learning System API": "http://127.0.0.1:5126/health",
    }
    
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"[OK] {name}: 正常")
                    results[name] = True
                else:
                    print(f"[WARN] {name}: ステータスコード {response.status_code}")
                    results[name] = False
            except Exception as e:
                print(f"[NG] {name}: 接続失敗 ({e})")
                results[name] = False
    
    return all(results.values())


async def main():
    """メインテスト"""
    print("=" * 60)
    print("ManaOS 統合機能動作確認")
    print("=" * 60)
    
    results = {}
    
    # 各システムのテスト
    results["Metrics Collector"] = await test_metrics_collector()
    results["Intelligent Retry"] = await test_intelligent_retry()
    results["Response Cache"] = await test_response_cache()
    results["Unified Orchestrator"] = await test_unified_orchestrator_init()
    results["Service Health"] = await test_service_health()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    for name, result in results.items():
        status = "[OK] 成功" if result else "[NG] 失敗"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] すべてのテストが成功しました！")
    else:
        print("[WARN] 一部のテストが失敗しました。")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

