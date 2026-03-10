"""
Pixel 7 ADB操作ヘルパー
ADB経由でPixel 7を制御・監視するためのユーティリティ
"""

import subprocess
import json
import re
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Pixel7ADBHelper:
    """Pixel 7 ADB操作ヘルパークラス"""
    
    def __init__(self, adb_path: str = "adb"):
        """
        Args:
            adb_path: ADBコマンドのパス（デフォルト: "adb"）
        """
        self.adb_path = adb_path
        self.device_id: Optional[str] = None
    
    def check_adb_available(self) -> bool:
        """ADBが利用可能か確認"""
        try:
            result = subprocess.run(
                [self.adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"ADB check failed: {e}")
            return False
    
    def get_devices(self) -> List[Dict[str, str]]:
        """接続されているデバイス一覧を取得"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 最初の行はヘッダー
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                device_id = parts[0]
                status = parts[1]
                
                # モデル名を抽出
                model = "unknown"
                for part in parts:
                    if part.startswith("model:"):
                        model = part.split(":")[1]
                        break
                
                devices.append({
                    "device_id": device_id,
                    "status": status,
                    "model": model
                })
            
            return devices
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []
    
    def find_pixel7(self) -> Optional[str]:
        """Pixel 7デバイスを検索"""
        devices = self.get_devices()
        
        for device in devices:
            if device["status"] == "device":
                # Pixel 7の判定（モデル名またはデバイスIDで判定）
                model = device["model"].lower()
                if "pixel" in model or "pixel7" in model:
                    self.device_id = device["device_id"]
                    return device["device_id"]
        
        # Pixel 7が見つからない場合、最初の接続済みデバイスを使用
        for device in devices:
            if device["status"] == "device":
                self.device_id = device["device_id"]
                return device["device_id"]
        
        return None
    
    def get_device_info(self) -> Optional[Dict]:
        """デバイス情報を取得"""
        if not self.device_id:
            if not self.find_pixel7():
                return None
        
        try:
            info = {}
            
            # モデル名
            result = subprocess.run(  # type: ignore[call-arg]
                [self.adb_path, "-s", self.device_id, "shell", "getprop", "ro.product.model"],  # type: ignore
                capture_output=True,
                text=True,
                timeout=5
            )
            info["model"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Android バージョン
            result = subprocess.run(  # type: ignore[call-arg]
                [self.adb_path, "-s", self.device_id, "shell", "getprop", "ro.build.version.release"],  # type: ignore
                capture_output=True,
                text=True,
                timeout=5
            )
            info["android_version"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # ビルド番号
            result = subprocess.run(  # type: ignore[call-arg]
                [self.adb_path, "-s", self.device_id, "shell", "getprop", "ro.build.id"],  # type: ignore
                capture_output=True,
                text=True,
                timeout=5
            )
            info["build_id"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # シリアル番号
            result = subprocess.run(  # type: ignore[call-arg]
                [self.adb_path, "-s", self.device_id, "shell", "getprop", "ro.serialno"],  # type: ignore
                capture_output=True,
                text=True,
                timeout=5
            )
            info["serial"] = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # バッテリー情報
            battery_info = self.get_battery_info()
            if battery_info:
                info["battery"] = battery_info
            
            # ストレージ情報
            storage_info = self.get_storage_info()
            if storage_info:
                info["storage"] = storage_info
            
            return info
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return None
    
    def get_battery_info(self) -> Optional[Dict]:
        """バッテリー情報を取得"""
        if not self.device_id:
            return None
        
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            battery_info = {}
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    battery_info["level"] = int(re.search(r'level:\s*(\d+)', line).group(1))  # type: ignore[union-attr]
                elif 'status:' in line:
                    battery_info["status"] = int(re.search(r'status:\s*(\d+)', line).group(1))  # type: ignore[union-attr]
                elif 'temperature:' in line:
                    battery_info["temperature"] = int(re.search(r'temperature:\s*(\d+)', line).group(1)) / 10.0  # type: ignore[union-attr]
            
            return battery_info
        except Exception as e:
            logger.error(f"Failed to get battery info: {e}")
            return None
    
    def get_storage_info(self) -> Optional[Dict]:
        """ストレージ情報を取得"""
        if not self.device_id:
            return None
        
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", "df", "/data"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # dfコマンドの出力をパース
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return None
            
            parts = lines[1].split()
            if len(parts) < 4:
                return None
            
            total_kb = int(parts[1])
            used_kb = int(parts[2])
            available_kb = int(parts[3])
            
            return {
                "total_gb": round(total_kb / 1024 / 1024, 2),
                "used_gb": round(used_kb / 1024 / 1024, 2),
                "available_gb": round(available_kb / 1024 / 1024, 2),
                "usage_percent": round((used_kb / total_kb) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return None
    
    def take_screenshot(self, output_path: str = None) -> Optional[str]:  # type: ignore
        """スクリーンショットを取得"""
        if not self.device_id:
            return None
        
        try:
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"pixel7_screenshot_{timestamp}.png"
            
            # デバイス上でスクリーンショットを取得
            remote_path = "/sdcard/screenshot.png"
            subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", "screencap", "-p", remote_path],
                capture_output=True,
                timeout=10
            )
            
            # PCにコピー
            subprocess.run(
                [self.adb_path, "-s", self.device_id, "pull", remote_path, output_path],
                capture_output=True,
                timeout=10
            )
            
            # デバイス上のファイルを削除
            subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", "rm", remote_path],
                capture_output=True,
                timeout=5
            )
            
            return output_path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def send_notification(self, title: str, text: str, package: str = "com.android.systemui") -> bool:
        """通知を送信"""
        if not self.device_id:
            return False
        
        try:
            # Android 7.0以降の通知送信コマンド
            cmd = f'am broadcast -a android.intent.action.SHOW_ALERT -e title "{title}" -e text "{text}"'
            result = subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", cmd],
                capture_output=True,
                timeout=5
            )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def get_logcat(self, lines: int = 100, filter_tag: str = None) -> Optional[str]:  # type: ignore
        """ログを取得"""
        if not self.device_id:
            return None
        
        try:
            cmd = [self.adb_path, "-s", self.device_id, "logcat", "-d", "-t", str(lines)]
            
            if filter_tag:
                cmd.extend(["-s", filter_tag])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"Failed to get logcat: {e}")
            return None
    
    def execute_command(self, command: str) -> Optional[str]:
        """コマンドを実行"""
        if not self.device_id:
            return None
        
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.device_id, "shell", command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return None


def main():
    """テスト用メイン関数"""
    helper = Pixel7ADBHelper()
    
    print("=== Pixel 7 ADB Helper Test ===\n")
    
    # ADB確認
    if not helper.check_adb_available():
        print("❌ ADB is not available")
        return
    
    print("✅ ADB is available\n")
    
    # デバイス検索
    device_id = helper.find_pixel7()
    if not device_id:
        print("❌ Pixel 7 not found")
        devices = helper.get_devices()
        if devices:
            print(f"Found {len(devices)} device(s):")
            for dev in devices:
                print(f"  - {dev['device_id']} ({dev['status']})")
        return
    
    print(f"✅ Pixel 7 found: {device_id}\n")
    
    # デバイス情報取得
    info = helper.get_device_info()
    if info:
        print("=== Device Info ===")
        print(json.dumps(info, indent=2, ensure_ascii=False))
        print()
    
    # バッテリー情報
    battery = helper.get_battery_info()
    if battery:
        print("=== Battery Info ===")
        print(f"Level: {battery.get('level', 'N/A')}%")
        print(f"Status: {battery.get('status', 'N/A')}")
        print(f"Temperature: {battery.get('temperature', 'N/A')}°C")
        print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()







