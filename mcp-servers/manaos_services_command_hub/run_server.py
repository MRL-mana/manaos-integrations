#!/usr/bin/env python3
"""サーバー起動スクリプト"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def main():
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

    # 起動待機
    print("⏳ 起動を待機中...")
    for i in range(10):
        time.sleep(1)
        try:
            response = requests.get("http://localhost:9404/health", timeout=1)
            if response.status_code == 200:
                print("✅ サーバーが起動しました！")

                # エンドポイントテスト
                print("\n📊 動作確認:")
                headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
                try:
                    r = requests.get(
                        "http://localhost:9404/remi/status", headers=headers, timeout=2)
                    if r.status_code == 200:
                        print("   ✅ /remi/status: OK")
                    else:
                        print(f"   ⚠️  /remi/status: {r.status_code}")
                except:
                    print("   ⚠️  /remi/status: エラー")

                return
        except:
            pass

    print("⚠️  起動確認ができませんでした。ログを確認してください。")


if __name__ == "__main__":
    main()





