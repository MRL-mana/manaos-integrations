#!/usr/bin/env python3
"""クイックスタートスクリプト - サーバーを起動して動作確認"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def start_server():
    """サーバーを起動"""
    work_dir = Path("/root/manaos_command_hub")

    print("🚀 マナOS Command Hub サーバーを起動します...")

    # 既存プロセスを停止
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*main:app.*9404"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"   既存プロセスを停止: PID {pid}")
                    subprocess.run(["kill", "-9", pid], capture_output=True)
            time.sleep(2)
    except:
        pass

    # サーバー起動
    log_file = work_dir / "logs" / "server.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "9404"
    ]

    with open(log_file, "w") as f:
        process = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=f,
            stderr=subprocess.STDOUT
        )

    print(f"✅ サーバーを起動しました (PID: {process.pid})")
    print(f"   ログ: {log_file}")

    # 起動待機
    print("\n⏳ サーバーの起動を待機中...")
    for i in range(10):
        time.sleep(1)
        try:
            response = requests.get("http://127.0.0.1:9404/health", timeout=1)
            if response.status_code == 200:
                print("✅ サーバーが正常に起動しました！")
                return True
        except:
            print(f"   {i+1}/10秒待機中...", end="\r")

    print("\n⚠️  サーバーの起動確認ができませんでした")
    print(f"   ログを確認してください: tail -20 {log_file}")
    return False


def test_endpoints():
    """エンドポイントをテスト"""
    print("\n📊 エンドポイントの動作確認:")

    # Health check
    try:
        response = requests.get("http://127.0.0.1:9404/health", timeout=2)
        print(f"   /health: {response.status_code}")
        if response.status_code == 200:
            print(f"      ✅ OK")
    except Exception as e:
        print(f"   /health: ❌ {e}")

    # Remi status
    try:
        headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
        response = requests.get(
            "http://127.0.0.1:9404/remi/status",
            headers=headers,
            timeout=2
        )
        print(f"   /remi/status: {response.status_code}")
        if response.status_code == 200:
            print(f"      ✅ OK")
            data = response.json()
            print(f"      サービス数: {len(data.get('services', {}))}")
        else:
            print(f"      ❌ {response.text[:100]}")
    except Exception as e:
        print(f"   /remi/status: ❌ {e}")


def main():
    print("="*60)
    print("マナOS Command Hub クイックスタート")
    print("="*60)
    print()

    if start_server():
        test_endpoints()
        print("\n" + "="*60)
        print("✅ セットアップ完了！")
        print("="*60)
        print("\n📝 次のステップ:")
        print("   - MCPツールで状態確認を試してください")
        print("   - ログ: tail -f /root/manaos_command_hub/logs/server.log")
    else:
        print("\n" + "="*60)
        print("❌ サーバーの起動に失敗しました")
        print("="*60)


if __name__ == "__main__":
    main()





