#!/usr/bin/env python3
"""
🔍 Device Health Monitor with Notifications - 通知機能付きデバイス監視
Device Health MonitorとNotification Hub Enhancedを統合
"""

from manaos_logger import get_logger, get_service_logger
import signal
import sys
from pathlib import Path

# ログ設定
logger = get_service_logger("device-monitor-with-notifications")
# モジュールをインポート
try:
    from device_health_monitor import DeviceHealthMonitor
    from notification_hub_enhanced import NotificationHubEnhanced
except ImportError as e:
    logger.error(f"モジュールのインポートエラー: {e}")
    sys.exit(1)


class DeviceMonitorWithNotifications:
    """通知機能付きデバイス監視システム"""
    
    def __init__(self):
        """初期化"""
        logger.info("Device Monitor with Notificationsを初期化します...")
        
        # Device Health Monitorを初期化
        self.health_monitor = DeviceHealthMonitor()
        
        # Notification Hub Enhancedを初期化
        self.notification_hub = NotificationHubEnhanced()
        
        # シグナルハンドラーを設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        logger.info(f"シグナル {signum} を受信しました。監視を停止します...")
        self.running = False
    
    def run(self):
        """監視ループを実行"""
        logger.info("Device Monitor with Notificationsを開始します...")
        
        # 初回通知（起動通知）
        self.notification_hub.send_notification(
            "🔍 Device Health Monitorが起動しました",
            priority="normal",
            context={"event": "startup"}
        )
        
        try:
            # 監視ループを実行
            self.health_monitor.run_monitoring_loop(self.notification_hub)
        except KeyboardInterrupt:
            logger.info("監視を停止します...")
        except Exception as e:
            logger.error(f"監視ループエラー: {e}")
            self.notification_hub.send_notification(
                f"❌ Device Health Monitorでエラーが発生しました: {str(e)}",
                priority="critical",
                context={"event": "error", "error": str(e)}
            )
        finally:
            # 終了通知
            self.notification_hub.send_notification(
                "🔍 Device Health Monitorが停止しました",
                priority="normal",
                context={"event": "shutdown"}
            )
            
            # 統計を表示
            stats = self.notification_hub.get_stats()
            logger.info(f"通知統計: {stats}")


def main():
    """メイン関数"""
    monitor = DeviceMonitorWithNotifications()
    monitor.run()


if __name__ == "__main__":
    main()

