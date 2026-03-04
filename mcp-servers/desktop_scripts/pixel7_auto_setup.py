"""
Pixel 7 自動セットアップスクリプト
USB接続後の自動セットアップを実行
"""

import subprocess
import sys
import time
import os
from pathlib import Path
from pixel7_adb_helper import Pixel7ADBHelper

def print_step(step_num: int, message: str):
    """ステップ表示"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {message}")
    print('='*60)

def check_adb_installed() -> bool:
    """ADBがインストールされているか確認"""
    try:
        result = subprocess.run(
            ["adb", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_adb_guide():
    """ADBインストールガイドを表示"""
    print("\n⚠️  ADBがインストールされていません")
    print("\nADBのインストール方法:")
    print("1. Android SDK Platform Toolsをダウンロード:")
    print("   https://developer.android.com/studio/releases/platform-tools")
    print("2. 解凍して任意のフォルダに配置（例: C:\\platform-tools）")
    print("3. 環境変数PATHに追加")
    print("\nまたは、Chocolateyを使用:")
    print("   choco install adb")

def check_pixel7_developer_options():
    """開発者オプションの有効化を確認"""
    print("\n📱 Pixel 7側の設定が必要です:")
    print("1. 設定 > 端末情報 > ビルド番号を7回タップ")
    print("2. 設定 > システム > 開発者オプション > USBデバッグをON")
    print("3. USBケーブルでPCに接続")
    print("4. 「USBデバッグを許可しますか？」で「許可」をタップ")
    print("5. 「常にこのコンピューターから許可する」にチェック（推奨）")
    
    input("\n設定が完了したらEnterキーを押してください...")

def wait_for_device(max_wait: int = 60):
    """デバイスの接続を待つ"""
    print(f"\n⏳ デバイスの接続を待っています（最大{max_wait}秒）...")
    
    helper = Pixel7ADBHelper()
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        devices = helper.get_devices()
        connected_devices = [d for d in devices if d["status"] == "device"]
        
        if connected_devices:
            print(f"✅ {len(connected_devices)}台のデバイスが接続されました")
            for dev in connected_devices:
                print(f"   - {dev['device_id']} ({dev.get('model', 'unknown')})")
            return True
        
        time.sleep(2)
        print(".", end="", flush=True)
    
    print("\n❌ デバイスが接続されませんでした")
    return False

def setup_directories():
    """必要なディレクトリを作成"""
    print_step(1, "ディレクトリのセットアップ")
    
    directories = [
        "screenshots",
        "logs",
        "backups"
    ]
    
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ {dir_name}/ ディレクトリを作成")
    
    return True

def check_dependencies():
    """依存パッケージの確認とインストール"""
    print_step(2, "依存パッケージの確認")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} インストール済み")
        except ImportError:
            print(f"❌ {package} が見つかりません")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  以下のパッケージをインストールします:")
        print(f"   {', '.join(missing_packages)}")
        
        response = input("インストールしますか？ (y/n): ")
        if response.lower() == 'y':
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + missing_packages,
                    check=True
                )
                print("✅ パッケージのインストールが完了しました")
            except subprocess.CalledProcessError:
                print("❌ パッケージのインストールに失敗しました")
                print("手動でインストールしてください:")
                print(f"   pip install {' '.join(missing_packages)}")
                return False
        else:
            print("⚠️  パッケージのインストールをスキップしました")
            return False
    
    return True

def verify_device_connection():
    """デバイス接続の確認"""
    print_step(3, "デバイス接続の確認")
    
    helper = Pixel7ADBHelper()
    
    if not helper.check_adb_available():
        print("❌ ADBが利用できません")
        install_adb_guide()
        return False
    
    print("✅ ADBが利用可能です")
    
    device_id = helper.find_pixel7()
    if not device_id:
        print("❌ Pixel 7が見つかりません")
        check_pixel7_developer_options()
        
        if not wait_for_device():
            return False
        
        device_id = helper.find_pixel7()
        if not device_id:
            print("❌ デバイスの接続に失敗しました")
            return False
    
    print(f"✅ Pixel 7が見つかりました: {device_id}")
    
    # デバイス情報を取得
    info = helper.get_device_info()
    if info:
        print(f"\n📱 デバイス情報:")
        print(f"   モデル: {info.get('model', 'N/A')}")
        print(f"   Android: {info.get('android_version', 'N/A')}")
        print(f"   シリアル: {info.get('serial', 'N/A')}")
        
        battery = info.get('battery')
        if battery:
            print(f"   バッテリー: {battery.get('level', 'N/A')}%")
    
    return True

def create_startup_script():
    """起動スクリプトを作成"""
    print_step(4, "起動スクリプトの作成")
    
    script_content = """@echo off
echo Starting ManaOS Pixel 7 Hub...
python manaos_pixel7_hub.py
pause
"""
    
    script_path = "start_pixel7_hub.bat"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print(f"✅ {script_path} を作成しました")
    
    # PowerShell版も作成
    ps_script_content = """Write-Host "Starting ManaOS Pixel 7 Hub..." -ForegroundColor Green
python manaos_pixel7_hub.py
Read-Host "Press Enter to exit"
"""
    
    ps_script_path = "start_pixel7_hub.ps1"
    with open(ps_script_path, "w", encoding="utf-8") as f:
        f.write(ps_script_content)
    
    print(f"✅ {ps_script_path} を作成しました")
    
    return True

def create_config_file():
    """設定ファイルを作成"""
    print_step(5, "設定ファイルの作成")
    
    config_content = """# Pixel 7 ManaOS統合設定

# Pixel7 Hub設定
PIXEL7_HUB_PORT=9405
PIXEL7_HUB_HOST=0.0.0.0

# 統合API設定
PIXEL7_INTEGRATION_PORT=9406
PIXEL7_INTEGRATION_HOST=0.0.0.0

# 秘書API設定（既存の秘書APIがある場合）
SECRETARY_API_URL=http://127.0.0.1:8080

# API Key設定（オプション）
PIXEL7_API_KEY=

# スクリーンショット保存先
PIXEL7_SCREENSHOT_DIR=./screenshots
"""
    
    config_path = ".env.pixel7"
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)
        print(f"✅ {config_path} を作成しました")
    else:
        print(f"ℹ️  {config_path} は既に存在します")
    
    return True

def run_quick_test():
    """クイックテストを実行"""
    print_step(6, "クイックテストの実行")
    
    helper = Pixel7ADBHelper()
    
    # バッテリー情報取得テスト
    print("\n🔋 バッテリー情報取得テスト...")
    battery = helper.get_battery_info()
    if battery:
        print(f"✅ バッテリー: {battery.get('level', 'N/A')}%")
    else:
        print("⚠️  バッテリー情報を取得できませんでした")
    
    # ストレージ情報取得テスト
    print("\n💾 ストレージ情報取得テスト...")
    storage = helper.get_storage_info()
    if storage:
        print(f"✅ ストレージ: {storage.get('available_gb', 'N/A')}GB 利用可能")
    else:
        print("⚠️  ストレージ情報を取得できませんでした")
    
    return True

def main():
    """メイン関数"""
    print("="*60)
    print("Pixel 7 ManaOS統合 自動セットアップ")
    print("="*60)
    
    # ADB確認
    if not check_adb_installed():
        install_adb_guide()
        print("\n❌ ADBのインストールが必要です")
        return False
    
    print("✅ ADBがインストールされています")
    
    # Pixel 7側の設定確認
    check_pixel7_developer_options()
    
    # セットアップ実行
    steps = [
        ("ディレクトリセットアップ", setup_directories),
        ("依存パッケージ確認", check_dependencies),
        ("デバイス接続確認", verify_device_connection),
        ("起動スクリプト作成", create_startup_script),
        ("設定ファイル作成", create_config_file),
        ("クイックテスト", run_quick_test),
    ]
    
    for step_name, step_func in steps:
        try:
            if not step_func():
                print(f"\n❌ {step_name}に失敗しました")
                return False
        except KeyboardInterrupt:
            print("\n\n⚠️  セットアップが中断されました")
            return False
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            return False
    
    # 完了メッセージ
    print("\n" + "="*60)
    print("✅ セットアップが完了しました！")
    print("="*60)
    
    print("\n📋 次のステップ:")
    print("1. Pixel7 Hubを起動:")
    print("   python manaos_pixel7_hub.py")
    print("   または")
    print("   .\\start_pixel7_hub.bat")
    print("\n2. ブラウザで以下にアクセス:")
    print("   http://127.0.0.1:9405/health")
    print("\n3. APIドキュメント:")
    print("   http://127.0.0.1:9405/docs")
    
    print("\n📚 詳細なドキュメント:")
    print("   - pixel7_setup_guide.md")
    print("   - PIXEL7_INTEGRATION_COMPLETE.md")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  セットアップが中断されました")
        sys.exit(1)







