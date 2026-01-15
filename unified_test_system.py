#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ManaOS統一テストシステム
全テストを統合管理・実行・結果集約
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from manaos_async_client import AsyncUnifiedAPIClient
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedTestSystem")

# キャッシュシステムの取得
cache_system = get_unified_cache()


class UnifiedTestSystem:
    """統一テストシステム"""
    
    def __init__(self):
        """初期化"""
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.test_history: List[Dict[str, Any]] = []
        
        logger.info("✅ Unified Test System初期化完了")
    
    async def test_all_services(self) -> Dict[str, Dict[str, Any]]:
        """
        全サービスのテストを実行（並列）
        
        Returns:
            テスト結果の辞書
        """
        async with AsyncUnifiedAPIClient() as client:
            # 全サービスのヘルスチェック（並列）
            health_results = await client.check_all_services()
            
            # テスト結果を整形
            results = {}
            for service, health in health_results.items():
                results[service] = {
                    "available": health.get("status") == "healthy",
                    "status": health.get("status", "unknown"),
                    "response_time": health.get("response_time", 0),
                    "timestamp": datetime.now().isoformat()
                }
            
            self.test_results["services"] = results
            return results
    
    async def test_integrations(self) -> Dict[str, Dict[str, Any]]:
        """
        統合システムのテストを実行
        
        Returns:
            テスト結果の辞書
        """
        results = {}
        
        # 各統合システムをテスト
        test_modules = [
            ("comfyui", "ComfyUI統合"),
            ("google_drive", "Google Drive統合"),
            ("obsidian", "Obsidian統合"),
            ("mem0", "Mem0統合"),
            ("civitai", "CivitAI統合"),
            ("github", "GitHub統合"),
        ]
        
        for module_name, display_name in test_modules:
            try:
                module = __import__(f"{module_name}_integration")
                integration_class = getattr(module, f"{module_name.title().replace('_', '')}Integration", None)
                
                if integration_class:
                    instance = integration_class()
                    results[module_name] = {
                        "available": instance.is_available(),
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    results[module_name] = {
                        "available": False,
                        "status": "class_not_found",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                results[module_name] = {
                    "available": False,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        self.test_results["integrations"] = results
        return results
    
    async def test_optimization_systems(self) -> Dict[str, Dict[str, Any]]:
        """
        最適化システムのテストを実行
        
        Returns:
            テスト結果の辞書
        """
        results = {}
        
        # 各最適化システムをテスト
        test_systems = [
            ("unified_cache_system", "統一キャッシュシステム"),
            ("database_connection_pool", "データベース接続プール"),
            ("http_session_pool", "HTTPセッションプール"),
            ("config_cache", "設定ファイルキャッシュ"),
        ]
        
        for module_name, display_name in test_systems:
            try:
                module = __import__(module_name)
                
                # テスト実行
                if module_name == "unified_cache_system":
                    cache = module.get_unified_cache()
                    cache.set("test", "value", test_key="test")
                    result = cache.get("test", test_key="test")
                    results[module_name] = {
                        "available": result == "value",
                        "status": "success" if result == "value" else "failed",
                        "timestamp": datetime.now().isoformat()
                    }
                elif module_name == "database_connection_pool":
                    pool = module.get_pool("test.db")
                    with pool.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        results[module_name] = {
                            "available": True,
                            "status": "success",
                            "timestamp": datetime.now().isoformat()
                        }
                elif module_name == "http_session_pool":
                    pool = module.get_http_session_pool()
                    stats = pool.get_stats()
                    results[module_name] = {
                        "available": True,
                        "status": "success",
                        "stats": stats,
                        "timestamp": datetime.now().isoformat()
                    }
                elif module_name == "config_cache":
                    cache = module.get_config_cache()
                    stats = cache.get_stats()
                    results[module_name] = {
                        "available": True,
                        "status": "success",
                        "stats": stats,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                results[module_name] = {
                    "available": False,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        self.test_results["optimization_systems"] = results
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        全テストを実行
        
        Returns:
            全テスト結果
        """
        logger.info("全テストを開始...")
        
        # 並列でテストを実行
        services_results, integrations_results, optimization_results = await asyncio.gather(
            self.test_all_services(),
            self.test_integrations(),
            self.test_optimization_systems(),
            return_exceptions=True
        )
        
        # 例外を処理
        if isinstance(services_results, Exception):
            services_results = {"error": str(services_results)}
        if isinstance(integrations_results, Exception):
            integrations_results = {"error": str(integrations_results)}
        if isinstance(optimization_results, Exception):
            optimization_results = {"error": str(optimization_results)}
        
        # 結果をまとめる
        all_results = {
            "services": services_results,
            "integrations": integrations_results,
            "optimization_systems": optimization_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # 統計を計算
        total_tests = 0
        passed_tests = 0
        
        for category, results in all_results.items():
            if isinstance(results, dict) and "error" not in results:
                for name, result in results.items():
                    total_tests += 1
                    if result.get("available") or result.get("status") == "success":
                        passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        # 履歴に追加
        self.test_history.append(all_results)
        
        # 最新10件のみ保持
        if len(self.test_history) > 10:
            self.test_history = self.test_history[-10:]
        
        logger.info(f"全テスト完了: {passed_tests}/{total_tests} 成功")
        
        return all_results
    
    def get_test_report(self) -> Dict[str, Any]:
        """テストレポートを取得"""
        if not self.test_history:
            return {"error": "テスト結果がありません"}
        
        latest = self.test_history[-1]
        
        return {
            "latest_test": latest,
            "test_count": len(self.test_history),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("統一テストシステムテスト")
    print("=" * 60)
    
    test_system = UnifiedTestSystem()
    
    # 全テストを実行
    results = asyncio.run(test_system.run_all_tests())
    
    # レポートを表示
    print("\nテスト結果:")
    print(json.dumps(results.get("summary", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()






















