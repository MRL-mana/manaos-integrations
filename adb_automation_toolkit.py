#!/usr/bin/env python3
"""
📱 ADB Automation Toolkit - Pixel 7自動化ツールキット
ADB接続の自動確立、スクリーンショット、アプリ操作、バッテリー監視
"""

import os
import subprocess
import json
import time
from manaos_logger import get_logger
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

logger = get_service_logger("adb-automation-toolkit")


@dataclass
class DeviceInfo:
    """デバイス情報"""
    device_id: str
    model: str
    android_version: str
    battery_level: int
    battery_status: str
    screen_on: bool
    connected: bool


@dataclass
class BatteryAlert:
    """バッテリーアラート"""
    level: int
    status: str
    timestamp: str
    alert_type: str  # "low", "critical", "charging", "full"


class ADBAutomationToolkit:
    """ADB自動化ツールキット"""
    
    def __init__(self, config_path: str = "adb_automation_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.device_ip = self.config.get("device_ip", "100.127.121.20")
        self.device_port = self.config.get("device_port", 5555)
        self.screenshot_dir = Path(self.config.get("screenshot_dir", "./screenshots"))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # バッテリー監視設定
        self.battery_alerts = {
            "low_threshold": self.config.get("battery_low_threshold", 20),
            "critical_threshold": self.config.get("battery_critical_threshold", 10),
            "full_threshold": self.config.get("battery_full_threshold", 95),
            "monitor_interval": self.config.get("battery_monitor_interval", 300)  # 5分
        }
        
        # ADBパスの確認
        self.adb_path = self._find_adb()
        if not self.adb_path:
            logger.error("ADBが見つかりません。PATHに追加するか、config.jsonでadb_pathを指定してください")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "device_ip": "100.127.121.20",
                "device_port": 5555,
                "screenshot_dir": "./screenshots",
                "battery_low_threshold": 20,
                "battery_critical_threshold": 10,
                "battery_full_threshold": 95,
                "battery_monitor_interval": 300,
                "adb_path": None  # Noneの場合はPATHから検索
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _find_adb(self) -> Optional[str]:
        """ADBのパスを検索"""
        # 設定ファイルで指定されている場合
        if self.config.get("adb_path"):
            adb_path = Path(self.config["adb_path"])
            if adb_path.exists():
                return str(adb_path)
        
        # PATHから検索
        try:
            result = subprocess.run(
                ["where", "adb"] if os.name == "nt" else ["which", "adb"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception as e:
            logger.warning(f"ADB検索エラー: {e}")
        
        return None
    
    def _run_adb_command(self, command: List[str], timeout: int = 10) -> Dict[str, Any]:
        """
        ADBコマンドを実行
        
        Args:
            command: ADBコマンド（例: ["devices"]）
            timeout: タイムアウト（秒）
        
        Returns:
            実行結果
        """
        if not self.adb_path:
            return {
                "success": False,
                "error": "ADBが見つかりません"
            }
        
        try:
            full_command = [self.adb_path] + command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"コマンドがタイムアウトしました（{timeout}秒）"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_connection(self) -> bool:
        """ADB接続を確認"""
        result = self._run_adb_command(["devices"])
        if not result["success"]:
            return False
        
        devices = result["stdout"]
        device_address = f"{self.device_ip}:{self.device_port}"
        return device_address in devices and "device" in devices
    
    def connect(self, force: bool = False) -> bool:
        """
        ADB接続を確立
        
        Args:
            force: 既存接続を切断して再接続
        
        Returns:
            成功時True
        """
        if force:
            self.disconnect()
        
        # 接続確認
        if self.check_connection():
            logger.info(f"既に接続されています: {self.device_ip}:{self.device_port}")
            return True
        
        # 接続を試みる
        logger.info(f"ADB接続を試みます: {self.device_ip}:{self.device_port}")
        result = self._run_adb_command(["connect", f"{self.device_ip}:{self.device_port}"])
        
        if result["success"]:
            # 接続確認
            time.sleep(2)
            if self.check_connection():
                logger.info("ADB接続が確立されました")
                return True
            else:
                logger.warning("ADB接続が確立されませんでした")
                return False
        else:
            logger.error(f"ADB接続エラー: {result.get('error', result.get('stderr', 'Unknown error'))}")
            return False
    
    def disconnect(self):
        """ADB接続を切断"""
        logger.info(f"ADB接続を切断します: {self.device_ip}:{self.device_port}")
        self._run_adb_command(["disconnect", f"{self.device_ip}:{self.device_port}"])
    
    def get_device_info(self) -> Optional[DeviceInfo]:
        """デバイス情報を取得"""
        if not self.check_connection():
            logger.warning("デバイスに接続されていません")
            return None
        
        try:
            # モデル名
            model_result = self._run_adb_command(["shell", "getprop", "ro.product.model"])
            model = model_result["stdout"].strip() if model_result["success"] else "Unknown"
            
            # Androidバージョン
            version_result = self._run_adb_command(["shell", "getprop", "ro.build.version.release"])
            android_version = version_result["stdout"].strip() if version_result["success"] else "Unknown"
            
            # バッテリーレベル
            battery_result = self._run_adb_command(["shell", "dumpsys", "battery"])
            battery_level = 0
            battery_status = "unknown"
            if battery_result["success"]:
                battery_output = battery_result["stdout"]
                for line in battery_output.split('\n'):
                    if "level:" in line:
                        battery_level = int(line.split(':')[1].strip())
                    if "status:" in line:
                        battery_status = line.split(':')[1].strip()
            
            # 画面状態
            screen_result = self._run_adb_command(["shell", "dumpsys", "power"])
            screen_on = False
            if screen_result["success"]:
                screen_output = screen_result["stdout"]
                screen_on = "mScreenOn=true" in screen_output or "mWakefulness=Awake" in screen_output
            
            return DeviceInfo(
                device_id=f"{self.device_ip}:{self.device_port}",
                model=model,
                android_version=android_version,
                battery_level=battery_level,
                battery_status=battery_status,
                screen_on=screen_on,
                connected=True
            )
        except Exception as e:
            logger.error(f"デバイス情報取得エラー: {e}")
            return None
    
    def take_screenshot(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        スクリーンショットを取得
        
        Args:
            filename: ファイル名（Noneの場合は自動生成）
        
        Returns:
            保存されたファイルのパス
        """
        if not self.check_connection():
            logger.warning("デバイスに接続されていません")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        screenshot_path = self.screenshot_dir / filename
        
        # スクリーンショットを取得
        result = self._run_adb_command(["exec-out", "screencap", "-p"], timeout=30)
        
        if result["success"]:
            try:
                # バイナリデータとして保存
                with open(screenshot_path, 'wb') as f:
                    # stdoutから直接バイナリデータを取得
                    screenshot_result = subprocess.run(
                        [self.adb_path, "-s", f"{self.device_ip}:{self.device_port}", "exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=30
                    )
                    if screenshot_result.returncode == 0:
                        f.write(screenshot_result.stdout)
                        logger.info(f"スクリーンショットを保存しました: {screenshot_path}")
                        return screenshot_path
            except Exception as e:
                logger.error(f"スクリーンショット保存エラー: {e}")
        else:
            logger.error(f"スクリーンショット取得エラー: {result.get('error', result.get('stderr', 'Unknown error'))}")
        
        return None
    
    def execute_shell_command(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Android shellコマンドを実行
        
        Args:
            command: 実行するコマンド
            timeout: タイムアウト（秒）
        
        Returns:
            実行結果
        """
        if not self.check_connection():
            return {
                "success": False,
                "error": "デバイスに接続されていません"
            }
        
        result = self._run_adb_command(["shell", command], timeout=timeout)
        return result
    
    def install_app(self, apk_path: str) -> bool:
        """
        アプリをインストール
        
        Args:
            apk_path: APKファイルのパス
        
        Returns:
            成功時True
        """
        if not self.check_connection():
            logger.warning("デバイスに接続されていません")
            return False
        
        apk_path_obj = Path(apk_path)
        if not apk_path_obj.exists():
            logger.error(f"APKファイルが見つかりません: {apk_path}")
            return False
        
        logger.info(f"アプリをインストールします: {apk_path}")
        result = self._run_adb_command(["install", str(apk_path_obj)], timeout=300)
        
        if result["success"]:
            logger.info("アプリのインストールが完了しました")
            return True
        else:
            logger.error(f"アプリのインストールエラー: {result.get('error', result.get('stderr', 'Unknown error'))}")
            return False
    
    def uninstall_app(self, package_name: str) -> bool:
        """
        アプリをアンインストール
        
        Args:
            package_name: パッケージ名
        
        Returns:
            成功時True
        """
        if not self.check_connection():
            logger.warning("デバイスに接続されていません")
            return False
        
        logger.info(f"アプリをアンインストールします: {package_name}")
        result = self._run_adb_command(["uninstall", package_name], timeout=60)
        
        if result["success"]:
            logger.info("アプリのアンインストールが完了しました")
            return True
        else:
            logger.error(f"アプリのアンインストールエラー: {result.get('error', result.get('stderr', 'Unknown error'))}")
            return False
    
    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """バッテリー情報を取得"""
        if not self.check_connection():
            return None
        
        result = self._run_adb_command(["shell", "dumpsys", "battery"])
        if not result["success"]:
            return None
        
        battery_info = {}
        for line in result["stdout"].split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                try:
                    # 数値に変換できる場合は変換
                    battery_info[key] = int(value) if value.isdigit() else value
                except ValueError:
                    battery_info[key] = value
        
        return battery_info
    
    def check_battery_alert(self) -> Optional[BatteryAlert]:
        """
        バッテリーアラートをチェック
        
        Returns:
            アラートがある場合BatteryAlert、ない場合None
        """
        battery_info = self.get_battery_info()
        if not battery_info:
            return None
        
        level = battery_info.get("level", 0)
        status = battery_info.get("status", "unknown")
        
        # 充電中
        if status == "2":  # BATTERY_STATUS_CHARGING
            if level >= self.battery_alerts["full_threshold"]:
                return BatteryAlert(
                    level=level,
                    status="charging",
                    timestamp=datetime.now().isoformat(),
                    alert_type="full"
                )
        
        # バッテリー残量が少ない
        if level <= self.battery_alerts["critical_threshold"]:
            return BatteryAlert(
                level=level,
                status=status,
                timestamp=datetime.now().isoformat(),
                alert_type="critical"
            )
        elif level <= self.battery_alerts["low_threshold"]:
            return BatteryAlert(
                level=level,
                status=status,
                timestamp=datetime.now().isoformat(),
                alert_type="low"
            )
        
        return None
    
    def monitor_battery(self, callback=None, interval: Optional[int] = None):
        """
        バッテリーを監視
        
        Args:
            callback: アラート発生時のコールバック関数
            interval: 監視間隔（秒、Noneの場合は設定値を使用）
        """
        monitor_interval = interval or self.battery_alerts["monitor_interval"]
        logger.info(f"バッテリー監視を開始します（間隔: {monitor_interval}秒）")
        
        while True:
            try:
                alert = self.check_battery_alert()
                if alert:
                    logger.warning(f"バッテリーアラート: {alert.alert_type} - {alert.level}%")
                    if callback:
                        callback(alert)
                
                time.sleep(monitor_interval)
            except KeyboardInterrupt:
                logger.info("バッテリー監視を停止します")
                break
            except Exception as e:
                logger.error(f"バッテリー監視エラー: {e}")
                time.sleep(monitor_interval)


def main():
    """メイン関数（テスト用）"""
    toolkit = ADBAutomationToolkit()
    
    # 接続確認
    if toolkit.connect():
        # デバイス情報を取得
        device_info = toolkit.get_device_info()
        if device_info:
            print(json.dumps(asdict(device_info), indent=2, ensure_ascii=False))
        
        # バッテリー情報を取得
        battery_info = toolkit.get_battery_info()
        if battery_info:
            print(f"\nバッテリー情報:")
            print(f"  レベル: {battery_info.get('level', 'Unknown')}%")
            print(f"  ステータス: {battery_info.get('status', 'Unknown')}")
    else:
        print("ADB接続に失敗しました")


if __name__ == "__main__":
    main()

