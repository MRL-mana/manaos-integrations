#!/usr/bin/env python3
"""
🔍 Device Health Monitor - デバイス健康状態監視システム
全デバイス（マナOS、母艦、X280、このはサーバー、Pixel 7）の健康状態を監視
"""

import os
import json
import time
import psutil
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from manaos_logger import get_logger

from _paths import ORCHESTRATOR_PORT
# ログ設定
logger = get_logger(__name__)


@dataclass
class DeviceHealth:
    """デバイスの健康状態"""
    device_name: str
    device_type: str  # "manaos", "mothership", "x280", "konoha", "pixel7"
    status: str  # "healthy", "warning", "critical", "offline"
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    uptime_seconds: float
    alerts: List[str]
    api_endpoint: Optional[str] = None


class DeviceHealthMonitor:
    """デバイス健康状態監視クラス"""

    def __init__(self, config_path: str = "device_health_config.json"):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.devices = self.config.get("devices", [])
        
        # 環境変数でデバイスエンドポイントを上書き
        for device in self.devices:
            device_type = device.get("type", "").upper()
            env_key = f"{device_type}_HEALTH_URL"
            env_url = os.getenv(env_key)
            if env_url:
                device["api_endpoint"] = env_url
                logger.info(f"Device {device['name']} endpoint overridden by {env_key}: {env_url}")
        
        self.check_interval = self.config.get("check_interval", 30)
        self.alert_thresholds = self.config.get("alert_thresholds", {
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "memory_warning": 85.0,
            "memory_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0
        })
        self.health_history: List[DeviceHealth] = []

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "devices": [
                    {
                        "name": "ManaOS",
                        "type": "manaos",
                        "api_endpoint": f"http://127.0.0.1:{ORCHESTRATOR_PORT}/health"
                    },
                    {
                        "name": "Mothership",
                        "type": "mothership",
                        # 重要: 母艦はメインのWindows PC（このコードが実行されているPC）
                        "api_endpoint": None  # ローカル監視
                    },
                    {
                        "name": "X280",
                        "type": "x280",
                        # 重要: X280は別のThinkPad Windows PC（母艦とは別のPC）
                        # Tailscale IP経由で接続: 100.127.121.20
                        "api_endpoint": "http://100.127.121.20:5120/health"
                    },
                    {
                        "name": "Konoha Server",
                        "type": "konoha",
                        "api_endpoint": "http://100.93.120.33:5106/health"
                    },
                    {
                        "name": "Pixel 7",
                        "type": "pixel7",
                        "api_endpoint": "http://100.84.2.125:5122/health"
                    }
                ],
                "check_interval": 30,
                "alert_thresholds": {
                    "cpu_warning": 80.0,
                    "cpu_critical": 95.0,
                    "memory_warning": 85.0,
                    "memory_critical": 95.0,
                    "disk_warning": 85.0,
                    "disk_critical": 95.0
                }
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config

    def check_local_health(self) -> DeviceHealth:
        """ローカルデバイスの健康状態をチェック"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # ネットワーク統計
            net_io = psutil.net_io_counters()
            network_sent_mb = net_io.bytes_sent / (1024 * 1024)
            network_recv_mb = net_io.bytes_recv / (1024 * 1024)

            # アップタイム
            uptime_seconds = time.time() - psutil.boot_time()

            # アラート生成
            alerts = []
            if cpu_percent >= self.alert_thresholds["cpu_critical"]:
                alerts.append(f"CPU使用率が危険レベル: {cpu_percent:.1f}%")
            elif cpu_percent >= self.alert_thresholds["cpu_warning"]:
                alerts.append(f"CPU使用率が警告レベル: {cpu_percent:.1f}%")

            if memory_percent >= self.alert_thresholds["memory_critical"]:
                alerts.append(f"メモリ使用率が危険レベル: {memory_percent:.1f}%")
            elif memory_percent >= self.alert_thresholds["memory_warning"]:
                alerts.append(f"メモリ使用率が警告レベル: {memory_percent:.1f}%")

            if disk_percent >= self.alert_thresholds["disk_critical"]:
                alerts.append(f"ディスク使用率が危険レベル: {disk_percent:.1f}%")
            elif disk_percent >= self.alert_thresholds["disk_warning"]:
                alerts.append(f"ディスク使用率が警告レベル: {disk_percent:.1f}%")

            # ステータス決定
            if any("危険レベル" in alert for alert in alerts):
                status = "critical"
            elif any("警告レベル" in alert for alert in alerts):
                status = "warning"
            else:
                status = "healthy"

            return DeviceHealth(
                device_name="Mothership",
                device_type="mothership",
                status=status,
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                uptime_seconds=uptime_seconds,
                alerts=alerts
            )
        except Exception as e:
            logger.error(f"ローカル健康状態チェックエラー: {e}")
            return DeviceHealth(
                device_name="Mothership",
                device_type="mothership",
                status="critical",
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                uptime_seconds=0.0,
                alerts=[f"監視エラー: {str(e)}"]
            )

    def check_remote_health(self, device_config: Dict[str, Any]) -> DeviceHealth:
        """リモートデバイスの健康状態をチェック"""
        api_endpoint = device_config.get("api_endpoint")
        device_name = device_config.get("name", "Unknown")
        device_type = device_config.get("type", "unknown")

        if not api_endpoint:
            return DeviceHealth(
                device_name=device_name,
                device_type=device_type,
                status="offline",
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                uptime_seconds=0.0,
                alerts=["APIエンドポイントが設定されていません"],
                api_endpoint=api_endpoint
            )

        try:
            # ヘルスチェックAPIを呼び出し
            response = requests.get(api_endpoint, timeout=5)
            if response.status_code == 200:
                health_data = response.json()

                # リモートデバイスの健康状態を取得
                return DeviceHealth(
                    device_name=device_name,
                    device_type=device_type,
                    status=health_data.get("status", "healthy"),
                    timestamp=datetime.now().isoformat(),
                    cpu_percent=health_data.get("cpu_percent", 0.0),
                    memory_percent=health_data.get("memory_percent", 0.0),
                    disk_percent=health_data.get("disk_percent", 0.0),
                    network_sent_mb=health_data.get("network_sent_mb", 0.0),
                    network_recv_mb=health_data.get("network_recv_mb", 0.0),
                    uptime_seconds=health_data.get("uptime_seconds", 0.0),
                    alerts=health_data.get("alerts", []),
                    api_endpoint=api_endpoint
                )
            else:
                return DeviceHealth(
                    device_name=device_name,
                    device_type=device_type,
                    status="warning",
                    timestamp=datetime.now().isoformat(),
                    cpu_percent=0.0,
                    memory_percent=0.0,
                    disk_percent=0.0,
                    network_sent_mb=0.0,
                    network_recv_mb=0.0,
                    uptime_seconds=0.0,
                    alerts=[f"API応答エラー: HTTP {response.status_code}"],
                    api_endpoint=api_endpoint
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"{device_name}への接続エラー: {e}")
            return DeviceHealth(
                device_name=device_name,
                device_type=device_type,
                status="offline",
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                uptime_seconds=0.0,
                alerts=[f"接続エラー: {str(e)}"],
                api_endpoint=api_endpoint
            )

    def check_all_devices(self) -> List[DeviceHealth]:
        """全デバイスの健康状態をチェック"""
        health_statuses = []

        for device_config in self.devices:
            device_type = device_config.get("type", "unknown")

            if device_type == "mothership":
                # ローカルデバイス
                health = self.check_local_health()
            else:
                # リモートデバイス
                health = self.check_remote_health(device_config)

            health_statuses.append(health)
            self.health_history.append(health)

            # 履歴を保持（最新100件）
            if len(self.health_history) > 100:
                self.health_history = self.health_history[-100:]

        return health_statuses

    def get_health_summary(self) -> Dict[str, Any]:
        """健康状態のサマリーを取得"""
        health_statuses = self.check_all_devices()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_devices": len(health_statuses),
            "healthy": sum(1 for h in health_statuses if h.status == "healthy"),
            "warning": sum(1 for h in health_statuses if h.status == "warning"),
            "critical": sum(1 for h in health_statuses if h.status == "critical"),
            "offline": sum(1 for h in health_statuses if h.status == "offline"),
            "devices": [asdict(h) for h in health_statuses]
        }

        return summary

    def get_all_devices_health(self) -> Dict[str, Any]:
        """全デバイスの健康状態を取得（統一インターフェース）"""
        return self.get_health_summary()

    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_health_summary()

    def run_monitoring_loop(self, notification_hub=None):
        """監視ループを実行

        Args:
            notification_hub: NotificationHubEnhancedインスタンス（オプション）
        """
        logger.info("Device Health Monitorを開始します...")

        while True:
            try:
                summary = self.get_health_summary()

                # ログ出力
                logger.info(f"監視結果: 正常={summary['healthy']}, "
                          f"警告={summary['warning']}, "
                          f"危険={summary['critical']}, "
                          f"オフライン={summary['offline']}")

                # アラートがある場合は通知
                for device in summary["devices"]:
                    if device["alerts"]:
                        logger.warning(f"{device['device_name']}: {device['alerts']}")

                        # 通知ハブが設定されている場合は通知を送信
                        if notification_hub:
                            priority = "critical" if device["status"] == "critical" else "important"
                            message = f"🔔 {device['device_name']} アラート:\n" + "\n".join(device["alerts"])
                            notification_hub.send_notification(
                                message,
                                priority=priority,
                                context={
                                    "device_name": device["device_name"],
                                    "device_type": device["device_type"],
                                    "status": device["status"]
                                }
                            )

                # 待機
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("監視を停止します...")
                break
            except Exception as e:
                logger.error(f"監視ループエラー: {e}")
                time.sleep(self.check_interval)


def main():
    """メイン関数"""
    monitor = DeviceHealthMonitor()

    # 一度だけチェック
    summary = monitor.get_health_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 監視ループを開始する場合は以下をコメントアウト
    # monitor.run_monitoring_loop()


if __name__ == "__main__":
    main()
