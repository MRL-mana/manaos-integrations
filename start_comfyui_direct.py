#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ComfyUIを直接起動するスクリプト"""

import subprocess
import os
import sys
import time
import io

# Windowsで日本語ログが文字化けしないようにUTF-8で出力
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, "buffer"):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def start_comfyui():
    """ComfyUIを起動"""
    comfyui_path = r"C:\ComfyUI"
    port = 8188

    # ComfyUIの存在確認
    if not os.path.exists(comfyui_path):
        print(f"[エラー] ComfyUIが見つかりません: {comfyui_path}")
        return False

    main_py = os.path.join(comfyui_path, "main.py")
    if not os.path.exists(main_py):
        print(f"[エラー] main.pyが見つかりません: {main_py}")
        return False

    # ポート使用状況確認
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result == 0:
            print(f"[情報] ポート {port} は既に使用中です")
            print(f"ComfyUIは既に起動している可能性があります")
            print(f"ブラウザで http://127.0.0.1:{port} にアクセスしてください")
            return True
    except Exception as e:
        print(f"[警告] ポート確認中にエラー: {e}")

    print(f"[起動中] ComfyUIを起動します...")
    print(f"  パス: {comfyui_path}")
    print(f"  ポート: {port}")
    print(f"")
    print(f"ブラウザで http://127.0.0.1:{port} にアクセスしてください")
    print(f"")

    try:
        # ComfyUIをバックグラウンドで起動
        # PIPEだとWindowsでtqdmのstderr flushがOSError 22を起こすため、DEVNULLにする
        process = subprocess.Popen(
            [sys.executable, "main.py", "--port", str(port)],
            cwd=comfyui_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        # 少し待って起動確認
        time.sleep(3)

        # プロセスがまだ実行中か確認
        if process.poll() is None:
            print(f"[成功] ComfyUIを起動しました (PID: {process.pid})")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"[エラー] ComfyUIの起動に失敗しました")
            if stderr:
                print(f"エラー出力: {stderr.decode('utf-8', errors='ignore')}")
            return False

    except Exception as e:
        print(f"[エラー] ComfyUIの起動中にエラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    start_comfyui()
