#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary 監視・アラート機能
ヘルスチェック、パフォーマンス監視、アラート送信
"""

import sys
import time
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from manaos_logger import get_logger
from _paths import FILE_SECRETARY_PORT

logger = get_service_logger("file-secretary-monitor")

DEFAULT_FILE_SECRETARY_API_URL = f"http://127.0.0.1:{FILE_SECRETARY_PORT}"


class FileSecretaryMonitor:
    """File Secretary監視システム"""
    
    def __init__(self, api_url: str = DEFAULT_FILE_SECRETARY_API_URL):
        """
        初期化
        
        Args:
            api_url: File Secretary API URL
        """
        self.api_url = api_url
        self.alert_thresholds = {
            "api_response_time": 5.0,  # 秒
            "database_size_mb": 100,  # MB
            "inbox_file_count": 100,  # 件
            "old_file_days": 7,  # 日
        }
    
    def check_api_health(self) -> Dict[str, Any]:
        """
        APIヘルスチェック
        
        Returns:
            ヘルスチェック結果
        """
        try:
            start_time = time.time()
            response = httpx.get(f"{self.api_url}/health", timeout=5.0)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "service": data.get("service"),
                    "version": data.get("version")
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_inbox_status(self) -> Dict[str, Any]:
        """
        INBOX状況確認
        
        Returns:
            INBOX状況
        """
        try:
            response = httpx.get(f"{self.api_url}/api/inbox/status", timeout=5.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_database_size(self) -> Dict[str, Any]:
        """
        データベースサイズ確認
        
        Returns:
            データベースサイズ情報
        """
        db_path = Path("file_secretary.db")
        if not db_path.exists():
            return {
                "status": "error",
                "error": "Database file not found"
            }
        
        size_bytes = db_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        return {
            "status": "ok",
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "threshold_mb": self.alert_thresholds["database_size_mb"]
        }
    
    def check_alerts(self) -> list:
        """
        アラートチェック
        
        Returns:
            アラートリスト
        """
        alerts = []
        
        # APIヘルスチェック
        health = self.check_api_health()
        if health.get("status") != "healthy":
            alerts.append({
                "level": "critical",
                "message": f"APIサーバーが応答しません: {health.get('error', 'unknown')}",
                "timestamp": datetime.now().isoformat()
            })
        elif health.get("response_time", 0) > self.alert_thresholds["api_response_time"]:
            alerts.append({
                "level": "warning",
                "message": f"API応答時間が遅いです: {health.get('response_time', 0):.2f}秒",
                "timestamp": datetime.now().isoformat()
            })
        
        # INBOX状況チェック
        inbox_status = self.check_inbox_status()
        if inbox_status.get("status") == "success":
            summary = inbox_status.get("summary", {})
            new_count = summary.get("new_count", 0)
            old_count = summary.get("old_count", 0)
            
            if new_count + old_count > self.alert_thresholds["inbox_file_count"]:
                alerts.append({
                    "level": "warning",
                    "message": f"INBOXファイル数が多すぎます: {new_count + old_count}件",
                    "timestamp": datetime.now().isoformat()
                })
            
            if old_count > 0:
                alerts.append({
                    "level": "info",
                    "message": f"未処理ファイルがあります: {old_count}件",
                    "timestamp": datetime.now().isoformat()
                })
        
        # データベースサイズチェック
        db_info = self.check_database_size()
        if db_info.get("status") == "ok":
            size_mb = db_info.get("size_mb", 0)
            if size_mb > self.alert_thresholds["database_size_mb"]:
                alerts.append({
                    "level": "warning",
                    "message": f"データベースサイズが大きいです: {size_mb}MB",
                    "timestamp": datetime.now().isoformat()
                })
        
        return alerts
    
    def generate_status_report(self) -> Dict[str, Any]:
        """
        ステータスレポート生成
        
        Returns:
            ステータスレポート
        """
        health = self.check_api_health()
        inbox_status = self.check_inbox_status()
        db_info = self.check_database_size()
        alerts = self.check_alerts()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "api_health": health,
            "inbox_status": inbox_status.get("summary", {}) if inbox_status.get("status") == "success" else {},
            "database": db_info,
            "alerts": alerts,
            "alert_count": len(alerts)
        }
    
    def run_monitoring_loop(self, interval_seconds: int = 60):
        """
        監視ループ実行
        
        Args:
            interval_seconds: 監視間隔（秒）
        """
        logger.info("監視ループ開始")
        
        try:
            while True:
                report = self.generate_status_report()
                
                # ログ出力
                logger.info(f"ステータス: API={report['api_health'].get('status')}, "
                          f"INBOX新規={report['inbox_status'].get('new_count', 0)}, "
                          f"アラート={report['alert_count']}")
                
                # アラート出力
                for alert in report['alerts']:
                    if alert['level'] == 'critical':
                        logger.error(f"🚨 {alert['message']}")
                    elif alert['level'] == 'warning':
                        logger.warning(f"⚠️ {alert['message']}")
                    else:
                        logger.info(f"ℹ️ {alert['message']}")
                
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("監視ループ停止")
        except Exception as e:
            logger.error(f"監視ループエラー: {e}")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='File Secretary 監視システム')
    parser.add_argument('--api-url', default=DEFAULT_FILE_SECRETARY_API_URL,
                       help='File Secretary API URL')
    parser.add_argument('--interval', type=int, default=60,
                       help='監視間隔（秒）')
    parser.add_argument('--once', action='store_true',
                       help='1回だけ実行して終了')
    
    args = parser.parse_args()
    
    monitor = FileSecretaryMonitor(api_url=args.api_url)
    
    if args.once:
        report = monitor.generate_status_report()
        print(f"\n=== File Secretary ステータスレポート ===")
        print(f"時刻: {report['timestamp']}")
        print(f"\nAPIヘルス: {report['api_health'].get('status')}")
        if report['api_health'].get('response_time'):
            print(f"応答時間: {report['api_health']['response_time']:.2f}秒")
        
        print(f"\nINBOX状況:")
        inbox = report['inbox_status']
        print(f"  新規: {inbox.get('new_count', 0)}件")
        print(f"  未処理: {inbox.get('old_count', 0)}件")
        
        print(f"\nデータベース:")
        db = report['database']
        if db.get('status') == 'ok':
            print(f"  サイズ: {db.get('size_mb', 0)}MB")
        
        print(f"\nアラート: {report['alert_count']}件")
        for alert in report['alerts']:
            level_icon = "🚨" if alert['level'] == 'critical' else "⚠️" if alert['level'] == 'warning' else "ℹ️"
            print(f"  {level_icon} {alert['message']}")
    else:
        monitor.run_monitoring_loop(interval_seconds=args.interval)


if __name__ == '__main__':
    main()






















