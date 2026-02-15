#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 ManaOSパフォーマンス最適化システム
全最適化機能を統合したマスターシステム
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from manaos_async_client import AsyncUnifiedAPIClient
from unified_cache_system import get_unified_cache
from database_connection_pool import get_pool
from http_session_pool import get_http_session_pool
from config_cache import get_config_cache

# ロガーの初期化
logger = get_service_logger("manaos-performance-optimizer")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PerformanceOptimizer")

app = Flask(__name__)
CORS(app)

# 最適化システム
cache_system = get_unified_cache()
http_pool = get_http_session_pool()
config_cache = get_config_cache()


class PerformanceOptimizer:
    """パフォーマンス最適化システム"""
    
    def __init__(self):
        """初期化"""
        self.optimization_history = []
        self.optimization_rules = []
    
    async def optimize_all_services_health_check(self) -> Dict[str, Any]:
        """全サービスのヘルスチェックを最適化（並列実行）"""
        try:
            async with AsyncUnifiedAPIClient() as client:
                start_time = datetime.now()
                results = await client.check_all_services()
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                stats = client.get_stats()
                
                return {
                    "status": "success",
                    "results": results,
                    "elapsed_time": elapsed_time,
                    "stats": stats,
                    "optimization": "parallel_execution"
                }
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"action": "optimize_all_services_health_check"},
                user_message="サービスヘルスチェックの最適化に失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or error.message
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        return cache_system.get_stats()
    
    def get_database_pool_stats(self, db_path: str) -> Dict[str, Any]:
        """データベースプール統計を取得"""
        try:
            pool = get_pool(db_path)
            return pool.get_stats()
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"db_path": db_path},
                user_message="データベースプール統計の取得に失敗しました"
            )
            return {"error": error.user_message or error.message}
    
    def get_http_pool_stats(self) -> Dict[str, Any]:
        """HTTPプール統計を取得"""
        return http_pool.get_stats()
    
    def get_config_cache_stats(self) -> Dict[str, Any]:
        """設定キャッシュ統計を取得"""
        return config_cache.get_stats()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """全統計情報を取得"""
        return {
            "cache": self.get_cache_stats(),
            "http_pool": self.get_http_pool_stats(),
            "config_cache": self.get_config_cache_stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    def optimize_cache(self) -> Dict[str, Any]:
        """キャッシュを最適化"""
        try:
            # 期限切れキャッシュのクリア（unified_cache_system内で自動処理）
            stats_before = cache_system.get_stats()
            
            # 統計情報を返す
            stats_after = cache_system.get_stats()
            
            return {
                "status": "success",
                "stats_before": stats_before,
                "stats_after": stats_after,
                "message": "キャッシュの最適化が完了しました"
            }
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"action": "optimize_cache"},
                user_message="キャッシュの最適化に失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or error.message
            }
    
    def optimize_all(self) -> Dict[str, Any]:
        """
        全システムを最適化（統一インターフェース）
        
        Returns:
            最適化結果
        """
        results = {
            "cache": {},
            "services_health_check": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # キャッシュの最適化
        try:
            results["cache"] = self.optimize_cache()
        except Exception as e:
            results["cache"] = {"status": "error", "error": str(e)}
        
        # サービスヘルスチェックの最適化（非同期）
        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                # 既にイベントループが実行中 — スレッドで実行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.optimize_all_services_health_check())
                    )
                    results["services_health_check"] = future.result(timeout=30)
            except RuntimeError:
                # イベントループなし — asyncio.run() で安全に実行
                results["services_health_check"] = asyncio.run(
                    self.optimize_all_services_health_check()
                )
        except Exception as e:
            results["services_health_check"] = {"status": "error", "error": str(e)}
        
        return results


optimizer = PerformanceOptimizer()


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Performance Optimizer"})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """全統計情報を取得"""
    try:
        stats = optimizer.get_all_stats()
        return jsonify(stats)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/stats"},
            user_message="統計情報の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/optimize/health-check', methods=['POST'])
def optimize_health_check():
    """サービスヘルスチェックを最適化"""
    try:
        result = asyncio.run(optimizer.optimize_all_services_health_check())
        return jsonify(result)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/optimize/health-check"},
            user_message="ヘルスチェックの最適化に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/optimize/cache', methods=['POST'])
def optimize_cache():
    """キャッシュを最適化"""
    try:
        result = optimizer.optimize_cache()
        return jsonify(result)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/optimize/cache"},
            user_message="キャッシュの最適化に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


def main():
    """テスト用メイン関数"""
    print("ManaOSパフォーマンス最適化システムテスト")
    print("=" * 60)
    
    # 統計情報を取得
    stats = optimizer.get_all_stats()
    print("\n統計情報:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # ヘルスチェック最適化テスト
    print("\nサービスヘルスチェック最適化テスト...")
    result = asyncio.run(optimizer.optimize_all_services_health_check())
    print(f"実行時間: {result.get('elapsed_time', 0):.2f}秒")


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5128))
    logger.info(f"🚀 Performance Optimizer起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")















