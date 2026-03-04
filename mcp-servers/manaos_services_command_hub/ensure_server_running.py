#!/usr/bin/env python3
"""
manaOS Command Hub サーバー起動確認・起動スクリプト
"""
import subprocess
import time
import requests
import sys
from pathlib import Path


def check_port(port):
    """ポートが使用されているか確認"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return f":{port}" in result.stdout
        except:
            return False


def check_server():
    """サーバーが応答するか確認"""
    try:
        response = requests.get("http://localhost:9404/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_server():
    """サーバーを起動"""
    print("Starting manaOS Command Hub server...")
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "9404"
    ]

    # バックグラウンドで起動
    process = subprocess.Popen(
        cmd,
        cwd="/root/manaos_command_hub",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 少し待ってから確認
    time.sleep(3)

    if process.poll() is None:
        print("✅ Server process started")
        return process
    else:
        stdout, stderr = process.communicate()
        print(f"❌ Server failed to start")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
        return None


def main():
    print("Checking manaOS Command Hub server status...")

    # ポート確認
    if check_port(9404):
        print("⚠️  Port 9404 is already in use")
        if check_server():
            print("✅ Server is responding")
            return 0
        else:
            print("❌ Port is in use but server is not responding")
            return 1

    # サーバー確認
    if check_server():
        print("✅ Server is already running")
        return 0

    # サーバー起動
    print("Server is not running. Starting...")
    process = start_server()

    if process is None:
        return 1

    # 起動確認
    time.sleep(2)
    if check_server():
        print("✅ Server started successfully")
        print(f"Process PID: {process.pid}")
        return 0
    else:
        print("❌ Server started but not responding")
        return 1


if __name__ == "__main__":
    sys.exit(main())






