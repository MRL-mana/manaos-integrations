#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像評価UI(9601) 自動起動ランチャー。ポート未使用時のみ起動し、二重起動を防ぐ。"""

import sys
import subprocess
from pathlib import Path

PORT = 9601


def is_port_in_use(port: int) -> bool:
    """ポートがLISTEN中か確認（接続できれば既に起動済み）"""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            return True
    except (OSError, socket.error):
        return False


def main():
    root = Path(__file__).resolve().parent
    script = root / "start_evaluation_ui_port9601.py"
    if not script.exists():
        return 1

    if is_port_in_use(PORT):
        return 0  # 既に起動済み

    # 子プロセスでサーバー起動（ウィンドウ非表示・親から切り離し）
    creationflags = 0
    if sys.platform == "win32":
        creationflags |= 0x08000000  # CREATE_NO_WINDOW
        creationflags |= 0x00000200  # CREATE_NEW_PROCESS_GROUP (子が独立)

    subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=(sys.platform != "win32"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
