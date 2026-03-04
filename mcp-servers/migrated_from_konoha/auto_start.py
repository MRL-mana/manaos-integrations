#!/usr/bin/env python3
"""
自動起動スクリプト - サーバーを起動してMCPツールで動作確認
"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def kill_existing():
    """既存のプロセスを停止"""
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
            return True
    except:
        pass
    return False


def start_server():
    """サーバーを起動"""
    work_dir = Path("/root/manaos_command_hub")
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

    return process, log_file


def wait_for_server(max_wait=15):
    """サーバーの起動を待つ"""
    for i in range(max_wait):
        try:
            response = requests.get("http://127.0.0.1:9404/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def test_remi_api():
    """Remi Control APIをテスト"""
    try:
        headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
        response = requests.get(
            "http://127.0.0.1:9404/remi/status",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ /remi/status: OK")
            print(f"      サービス数: {len(data.get('services', {}))}")
            return True
        else:
            print(f"   ⚠️  /remi/status: {response.status_code}")
            print(f"      レスポンス: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ /remi/status: {e}")
    return False


def main():
    print("="*60)
    print("🚀 マナOS Command Hub 自動起動")
    print("="*60)
    print()

    # 既存プロセスを停止
    if kill_existing():
        print("⚠️  既存のプロセスを停止しました")

    # サーバー起動
    print("📡 サーバーを起動中...")
    process, log_file = start_server()
    print(f"   PID: {process.pid}")
    print(f"   ログ: {log_file}")

    # 起動待機
    print("\n⏳ サーバーの起動を待機中...")
    if wait_for_server():
        print("✅ サーバーが起動しました！")

        # 動作確認
        print("\n📊 動作確認:")
        test_remi_api()

        print("\n" + "="*60)
        print("✅ セットアップ完了！")
        print("="*60)
        print("\n📝 次のステップ:")
        print("   - MCPツールで状態確認を試してください")
        print(f"   - ログ: tail -f {log_file}")
        print(f"   - 停止: kill {process.pid}")
    else:
        print("❌ サーバーの起動に失敗しました")
        print(f"   ログを確認してください: tail -20 {log_file}")
        if log_file.exists():
            print("\n最新のログ:")
            print(log_file.read_text()[-500:])


if __name__ == "__main__":
    main()

