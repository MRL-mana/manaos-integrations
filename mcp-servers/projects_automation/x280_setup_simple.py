#!/usr/bin/env python3
"""
X280セットアップ - シンプル版
SSHとPythonで直接セットアップ
"""

import subprocess

def run_x280_command(cmd):
    """X280でコマンドを実行"""
    try:
        result = subprocess.run(
            ["ssh", "x280", cmd],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🚀 X280 GUI自動操作システム セットアップ")
    print("=" * 60)
    
    # 1. Python確認
    print("\n📍 Step 1: Python確認...")
    success, stdout, stderr = run_x280_command("python --version")
    if success:
        print(f"✅ Python: {stdout.strip()}")
    else:
        print("❌ Python確認失敗")
        return
    
    # 2. Pythonでディレクトリ作成
    print("\n📍 Step 2: ディレクトリ作成...")
    create_dir_cmd = """python -c "import os; os.makedirs('C:/Users/mana/x280_gui_automation', exist_ok=True); os.makedirs('C:/Users/mana/x280_gui_automation/screenshots', exist_ok=True); os.makedirs('C:/Users/mana/x280_gui_automation/logs', exist_ok=True); print('Directories created')" """
    
    success, stdout, stderr = run_x280_command(create_dir_cmd)
    if success:
        print(f"✅ ディレクトリ作成: {stdout.strip()}")
    else:
        print(f"⚠️ ディレクトリ作成: {stderr}")
    
    # 3. パッケージインストール確認
    print("\n📍 Step 3: パッケージ確認...")
    packages = ["flask", "pyautogui", "pillow", "psutil"]
    for pkg in packages:
        check_cmd = f'python -c "import {pkg}; print(\\"{pkg} OK\\")"'
        success, stdout, stderr = run_x280_command(check_cmd)
        if success:
            print(f"   ✅ {pkg}: インストール済み")
        else:
            print(f"   ❌ {pkg}: 未インストール")
            print(f"      → pip install {pkg} が必要")
    
    # 4. 次のステップ
    print("\n" + "=" * 60)
    print("📝 次のステップ:")
    print("1. 不足しているパッケージをインストール:")
    print("   ssh x280 'python -m pip install flask flask-cors pyautogui pillow pytesseract psutil'")
    print("\n2. GUI APIサーバーコードを転送")
    print("\n3. X280でサーバー起動:")
    print("   ssh x280 'cd C:\\Users\\mana\\x280_gui_automation && python x280_gui_server.py'")
    print("=" * 60)

if __name__ == "__main__":
    main()


