"""
Pixel 7接続確認スクリプト（絵文字なし版）
"""

import subprocess
import sys
import os

def check_adb():
    """ADBが利用可能か確認"""
    try:
        result = subprocess.run(
            ["adb", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[OK] ADB is available")
            print(f"     Version: {result.stdout.strip()}")
            return True
        return False
    except FileNotFoundError:
        print("[NG] ADB is not installed")
        return False
    except Exception as e:
        print(f"[ERROR] ADB check failed: {e}")
        return False

def check_devices():
    """接続されているデバイスを確認"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("[ERROR] Failed to run adb devices")
            return False
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("[INFO] No devices connected")
            return False
        
        devices = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    if status == "device":
                        devices.append(device_id)
                        print(f"[OK] Device connected: {device_id}")
                    elif status == "unauthorized":
                        print(f"[WARNING] Device unauthorized: {device_id}")
                        print("         Please allow USB debugging on Pixel 7")
                    else:
                        print(f"[INFO] Device status ({status}): {device_id}")
        
        return len(devices) > 0
    except FileNotFoundError:
        print("[ERROR] ADB command not found")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to check devices: {e}")
        return False

def get_device_info():
    """デバイス情報を取得"""
    try:
        # デバイスIDを取得
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        device_id = None
        for line in result.stdout.split('\n'):
            if 'device' in line and 'unauthorized' not in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    device_id = parts[0]
                    break
        
        if not device_id:
            print("[INFO] No authorized device found")
            return False
        
        print(f"\n[INFO] Getting device information for {device_id}...")
        
        # モデル名
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True,
            timeout=5
        )
        model = result.stdout.strip() if result.returncode == 0 else "unknown"
        print(f"  Model: {model}")
        
        # Android バージョン
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"],
            capture_output=True,
            text=True,
            timeout=5
        )
        android_version = result.stdout.strip() if result.returncode == 0 else "unknown"
        print(f"  Android: {android_version}")
        
        # バッテリー情報
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    level = line.split(':')[1].strip()
                    print(f"  Battery: {level}%")
                    break
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to get device info: {e}")
        return False

def main():
    """メイン関数"""
    print("=" * 60)
    print("Pixel 7 Connection Check")
    print("=" * 60)
    
    # ADB確認
    print("\n[Step 1] Checking ADB...")
    if not check_adb():
        print("\n[SETUP REQUIRED] ADB installation needed")
        print("\nInstallation options:")
        print("1. Download Android SDK Platform Tools:")
        print("   https://developer.android.com/studio/releases/platform-tools")
        print("2. Or use Chocolatey (if installed):")
        print("   choco install adb")
        print("\nAfter installation, add ADB to PATH and run this script again.")
        return False
    
    # デバイス確認
    print("\n[Step 2] Checking connected devices...")
    if not check_devices():
        print("\n[SETUP REQUIRED] Device connection needed")
        print("\nPlease ensure:")
        print("1. USB cable is connected")
        print("2. USB debugging is enabled on Pixel 7")
        print("3. 'Allow USB debugging' dialog is accepted on Pixel 7")
        return False
    
    # デバイス情報取得
    print("\n[Step 3] Getting device information...")
    get_device_info()
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Pixel 7 is connected and ready!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Install dependencies:")
    print("   pip install -r requirements_pixel7.txt")
    print("\n2. Start Pixel7 Hub:")
    print("   python manaos_pixel7_hub.py")
    print("\n3. Check status:")
    print("   http://127.0.0.1:9405/health")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Check interrupted")
        sys.exit(1)






