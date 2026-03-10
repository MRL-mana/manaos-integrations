#!/usr/bin/env python3
"""環境診断スクリプト"""
import os
import sys
import subprocess
from pathlib import Path


def test_basic():
    """基本的な動作確認"""
    print("=== 基本動作確認 ===")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"User: {os.getenv('USER', 'unknown')}")
    print()


def test_subprocess():
    """subprocessの動作確認"""
    print("=== subprocess動作確認 ===")
    try:
        result = subprocess.run(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")
    print()


def test_file_access():
    """ファイルアクセスの確認"""
    print("=== ファイルアクセス確認 ===")
    work_dir = Path("/root/manaos_command_hub")
    main_file = work_dir / "main.py"
    print(f"Work directory exists: {work_dir.exists()}")
    print(f"main.py exists: {main_file.exists()}")
    if main_file.exists():
        print(f"main.py size: {main_file.stat().st_size} bytes")
    print()


def test_python_imports():
    """Pythonモジュールのインポート確認"""
    print("=== Pythonモジュール確認 ===")
    modules = ["fastapi", "uvicorn", "requests"]
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}: OK")
        except ImportError as e:
            print(f"❌ {module}: {e}")
    print()


def test_server_start():
    """サーバー起動テスト"""
    print("=== サーバー起動テスト ===")
    work_dir = Path("/root/manaos_command_hub")
    os.chdir(work_dir)

    try:
        # モジュールのインポートテスト
        sys.path.insert(0, str(work_dir))
        from main import app
        print("✅ main.py import: OK")
        print(f"   App: {app}")

        # ルート確認
        routes = [r.path for r in app.routes if hasattr(r, 'path')]  # type: ignore
        remi_routes = [r for r in routes if 'remi' in r]
        print(f"✅ Total routes: {len(routes)}")
        print(f"✅ Remi routes: {remi_routes}")

    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
    print()


def main():
    print("🔍 マナOS Command Hub 環境診断\n")
    test_basic()
    test_subprocess()
    test_file_access()
    test_python_imports()
    test_server_start()
    print("=== 診断完了 ===")


if __name__ == "__main__":
    main()





