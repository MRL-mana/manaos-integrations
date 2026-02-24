#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止めるまで画像生成を繰り返すラッパー。
Ctrl+C で停止。バッチごとに generate_50 を --no-wait で実行します。
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "generate_50_mana_mufufu_manaos.py"
BATCH_SIZE = 50
INTERVAL_SEC = 10  # バッチ間の待機秒（0でなし）


def main():
    if not SCRIPT.exists():
        print(f"エラー: {SCRIPT} が見つかりません")
        return 1

    batch = int(os.environ.get("MANAOS_LOOP_BATCH_SIZE", BATCH_SIZE))
    interval = float(os.environ.get("MANAOS_LOOP_INTERVAL_SEC", INTERVAL_SEC))

    # 既存の generate_50 のオプションをそのまま使う（環境変数でプロファイル等は可）
    base_cmd = [
        sys.executable,
        "-u",
        str(SCRIPT),
        "-n",
        str(batch),
        "--no-wait",
    ]
    # プロファイルは環境変数 MANAOS_IMAGE_DEFAULT_PROFILE またはここで追加
    profile = os.environ.get("MANAOS_IMAGE_DEFAULT_PROFILE", "").strip().lower()
    if profile in ("lab", "safe"):
        base_cmd.extend(["--profile", profile])

    print("=" * 60)
    print("止めるまで生成を繰り返します（Ctrl+C で停止）")
    print(f"  バッチ: {batch} 枚/回, 間隔: {interval} 秒")
    print(f"  コマンド: {' '.join(base_cmd)}")
    print("=" * 60)

    round_num = 0
    stop = False

    def on_sig(sig_num, frame):
        nonlocal stop
        stop = True
        print("\n[Ctrl+C] 停止します...")

    signal.signal(signal.SIGINT, on_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_sig)

    try:
        while not stop:
            round_num += 1
            print(f"\n--- ラウンド {round_num} (バッチ {batch} 枚) ---")
            ret = subprocess.run(base_cmd, cwd=str(ROOT))
            if ret.returncode != 0:
                print(f"警告: 終了コード {ret.returncode}。{interval} 秒後に再試行します。")
            if stop:
                break
            if interval > 0:
                for _ in range(int(interval)):
                    if stop:
                        break
                    time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("\n終了しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
