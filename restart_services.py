"""ManaOS サービス再起動スクリプト（安全版）

旧版は taskkill /F /IM python.exe で全Pythonプロセスを無差別に終了していたが、
ProcessManager を使って ManaOS 関連プロセスのみを安全に停止する。
"""

import subprocess
import time
import socket
from pathlib import Path

from manaos_process_manager import get_process_manager

try:
    from _paths import MRL_MEMORY_PORT, LEARNING_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT
except ImportError:
    MRL_MEMORY_PORT, LEARNING_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT = 5105, 5126, 5111, 9502

_SERVICE_PORTS = [
    ("MRL Memory", MRL_MEMORY_PORT),
    ("Learning", LEARNING_PORT),
    ("LLM Routing", LLM_ROUTING_PORT),
    ("Unified API", UNIFIED_API_PORT),
]

def main():
    pm = get_process_manager()

    print("[STOP] ManaOS サービスプロセスを停止中...")
    for name, port in _SERVICE_PORTS:
        killed = pm.kill_processes_by_port(port)
        if killed:
            print(f"  {name} (:{port}) → {killed} プロセス停止")
        else:
            print(f"  {name} (:{port}) → 実行中のプロセスなし")
    time.sleep(3)

    print("[START] サービスを再起動中...")
    subprocess.Popen(
        ["python", "start_vscode_cursor_services.py"],
        cwd=str(Path(__file__).resolve().parent),
    )
    print("[WAIT] 45秒待機中...")
    time.sleep(45)

    print("[CHECK] ポート状態:")
    for name, port in _SERVICE_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        status = "Open ✓" if result == 0 else "Closed ✗"
        print(f"  {name} (:{port}): {status}")


if __name__ == "__main__":
    main()
