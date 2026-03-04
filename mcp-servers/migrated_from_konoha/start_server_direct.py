#!/usr/bin/env python3
"""
マナOS Command Hub サーバー直接起動スクリプト
"""
import subprocess
import sys
import time
import os
from pathlib import Path


def main():
    # 作業ディレクトリに移動
    work_dir = Path(__file__).parent
    os.chdir(work_dir)

    print("🚀 マナOS Command Hub サーバーを起動します...")
    print(f"   作業ディレクトリ: {work_dir}")
    print(f"   ポート: 9404")
    print()

    # 既存のプロセスを確認
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*main:app.*9404"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("⚠️  既存のサーバープロセスが見つかりました")
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"   停止中: PID {pid}")
                    subprocess.run(["kill", "-9", pid], capture_output=True)
            time.sleep(2)
    except Exception as e:
        print(f"   プロセス確認スキップ: {e}")

    # サーバーを起動
    print("📡 サーバーを起動中...")
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "9404",
        "--log-level", "info"
    ]

    print(f"   コマンド: {' '.join(cmd)}")
    print()

    # バックグラウンドで起動
    log_file = work_dir / "logs" / "server.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "w") as f:
        process = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=f,
            stderr=subprocess.STDOUT
        )

    # プロセスIDを記録
    pid_file = Path("/tmp/command_hub.pid")
    pid_file.write_text(str(process.pid))

    print(f"✅ サーバープロセスを起動しました")
    print(f"   PID: {process.pid}")
    print(f"   ログ: {log_file}")
    print()

    # 起動確認
    print("⏳ サーバーの起動を待機中...")
    time.sleep(5)

    # プロセス確認
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*main:app.*9404"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ サーバーが正常に起動しています")
            print()
            print("📊 動作確認:")
            print("   Health: curl http://127.0.0.1:9404/health")
            print("   Status: curl -H 'X-Auth-Token: manaos-secret-token-please-change' http://127.0.0.1:9404/remi/status")
            print()
            print("📝 ログ: tail -f " + str(log_file))
            print("🛑 停止: kill " + str(process.pid))
        else:
            print("❌ サーバーの起動に失敗した可能性があります")
            print(f"   ログを確認してください: tail -20 {log_file}")
            if log_file.exists():
                print("\n最新のログ:")
                print(log_file.read_text()[-500:])
    except Exception as e:
        print(f"⚠️  プロセス確認エラー: {e}")
        print(f"   ログを確認してください: tail -20 {log_file}")


if __name__ == "__main__":
    main()





