#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[AUTO] ManaOS 自律運用システム（System3）
サービスの自動監視・診断・復旧を統合管理
"""

import time
import logging
import threading
import os
from typing import Any, Dict, Optional
from datetime import datetime

# 標準ライブラリのみ使用（依存関係を最小化）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class AutonomousOperations:
    """
    自律運用システム
    
    以下の機能を統合:
    - サービスヘルスチェック
    - 異常検知
    - 自動復旧（計画）
    - パフォーマンス監視
    """
    
    def __init__(
        self,
        check_interval: int = 60,
        enable_auto_recovery: bool = False
    ):
        """
        初期化
        
        Args:
            check_interval: チェック間隔（秒）
            enable_auto_recovery: 自動復旧を有効化（現在は計画のみ）
        """
        self.check_interval = check_interval
        self.enable_auto_recovery = enable_auto_recovery
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # サービス定義（Unified API は /ready で初期化完了を確認、タイムアウト長め）
        unified_api_port = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9510"))
        self.services = [
            {
                "name": "MRL Memory",
                "port": 5105,
                "path": "/health",
                "timeout": 5,
            },
            {
                "name": "Learning System",
                "port": 5126,
                "path": "/health",
                "timeout": 5,
            },
            {
                "name": "LLM Routing",
                "port": 5111,
                "path": "/health",
                "timeout": 5,
            },
            {
                "name": "Unified API",
                "port": unified_api_port,
                "path": "/ready",
                "timeout": 8,
            },
        ]
        
        # 統計情報
        self.stats: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "total_checks": 0,
            "health_failures": 0,
            "last_check_time": None,
            "service_status": {}
        }
        
        logger.info("[AUTO] 自律運用システムを初期化しました")
        logger.info(f"   監視間隔: {check_interval}秒")
        logger.info(f"   自動復旧: {'有効' if enable_auto_recovery else '無効（計画のみ）'}")
    
    def check_service_health(self, service: Dict) -> bool:
        """
        サービスのヘルスチェック（Unified API は /ready で初期化完了を確認）
        """
        try:
            import requests
            path = service.get("path", "/health")
            timeout = service.get("timeout", 5)
            url = f"http://127.0.0.1:{service['port']}{path}"
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except Exception as e:
            logger.warning(
                f"[WARN] {service['name']} (port {service['port']}): "
                f"ヘルスチェック失敗 - {e}"
            )
            return False
    
    def run_health_checks(self) -> Dict[str, bool]:
        """
        全サービスのヘルスチェック実行
        
        Returns:
            サービス名 -> 健全性のマップ
        """
        results = {}
        self.stats["total_checks"] += 1
        self.stats["last_check_time"] = datetime.now().isoformat()
        
        for service in self.services:
            is_healthy = self.check_service_health(service)
            results[service["name"]] = is_healthy
            
            # 統計を更新
            if service["name"] not in self.stats["service_status"]:
                self.stats["service_status"][service["name"]] = {
                    "total_checks": 0,
                    "failures": 0,
                    "last_status": None
                }
            
            self.stats["service_status"][service["name"]]["total_checks"] += 1
            self.stats["service_status"][service["name"]]["last_status"] = (
                "healthy" if is_healthy else "unhealthy"
            )
            
            if not is_healthy:
                self.stats["service_status"][service["name"]]["failures"] += 1
                self.stats["health_failures"] += 1
        
        return results
    
    def analyze_and_report(self, health_results: Dict[str, bool]):
        """
        ヘルスチェック結果を分析してレポート
        
        Args:
            health_results: サービス名 -> 健全性のマップ
        """
        unhealthy_services = [
            name
            for name, is_healthy in health_results.items()
            if not is_healthy
        ]
        
        if unhealthy_services:
            logger.warning(
                f"[WARN] 異常検知: {len(unhealthy_services)}個のサービスが応答しません"
            )
            for service_name in unhealthy_services:
                logger.warning(f"   - {service_name}")
            
            if self.enable_auto_recovery:
                logger.info("🔧 自動復旧を試みます...")
                # NOTE: stub — auto-recovery not yet implemented
                logger.warning("   （自動復旧機能は開発中）")
            else:
                logger.info("💡 手動での対処が必要です:")
                logger.info("   1. タスク \"ManaOS: サービスヘルスチェック\" を実行")
                logger.info("   2. 問題のあるサービスを再起動")
        else:
            logger.info("[OK] すべてのサービスが正常稼働中")
    
    def monitor_loop(self):
        """監視ループ"""
        logger.info("[MONITOR] 自律監視を開始しました")
        
        while self.running:
            try:
                # ヘルスチェック実行
                health_results = self.run_health_checks()
                
                # 分析とレポート
                self.analyze_and_report(health_results)
                
                # 次のチェックまで待機
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ 監視ループエラー: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """自律監視を開始"""
        if self.running:
            logger.warning("既に監視が実行中です")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            daemon=True,
        )
        self.monitor_thread.start()
        logger.info("[OK] 自律監視スレッドを起動しました")
    
    def stop(self):
        """自律監視を停止"""
        if not self.running:
            return
        
        logger.info("自律監視を停止中...")
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("[OK] 自律監視を停止しました")
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return {
            **self.stats,
            "uptime_seconds": (
                datetime.now()
                - datetime.fromisoformat(self.stats["start_time"])
            ).total_seconds()
        }
    
    def print_stats(self):
        """統計情報を表示"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 自律運用システム統計")
        print("=" * 60)
        print(f"稼働時間: {stats['uptime_seconds']:.0f}秒")
        print(f"総チェック回数: {stats['total_checks']}")
        print(f"異常検知回数: {stats['health_failures']}")
        print(f"最終チェック: {stats['last_check_time']}")
        
        if stats['service_status']:
            print("\n--- サービス別統計 ---")
            for service_name, service_stats in stats['service_status'].items():
                failure_rate = (
                    service_stats['failures']
                    / service_stats['total_checks']
                    * 100
                    if service_stats['total_checks'] > 0
                    else 0
                )
                print(f"{service_name}:")
                print(f"  チェック回数: {service_stats['total_checks']}")
                print(f"  異常回数: {service_stats['failures']}")
                print(f"  異常率: {failure_rate:.1f}%")
                print(f"  最終状態: {service_stats['last_status']}")
        
        print("=" * 60 + "\n")


def main():
    """テスト実行"""
    # 自律運用システムを初期化（チェック間隔30秒）
    autonomous = AutonomousOperations(
        check_interval=30,
        enable_auto_recovery=False,
    )
    
    # 監視開始
    autonomous.start()
    
    try:
        # 5分間実行（テスト用）
        logger.info("5分間の監視を開始します（Ctrl+Cで停止）")
        time.sleep(300)
    except KeyboardInterrupt:
        logger.info("\n停止シグナルを受け取りました")
    finally:
        # 統計表示
        autonomous.print_stats()
        
        # 停止
        autonomous.stop()


if __name__ == "__main__":
    main()
