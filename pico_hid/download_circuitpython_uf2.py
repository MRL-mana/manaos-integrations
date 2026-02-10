#!/usr/bin/env python3
"""
Pico 2 W 用 CircuitPython UF2 をダウンロードする。
ダウンロード後、表示される手順に従って Pico にコピーしてください。
"""

import sys
from pathlib import Path

try:
    import urllib.request
except ImportError:
    urllib.request = None

UF2_URL = "https://downloads.circuitpython.org/bin/raspberry_pi_pico2_w/en_US/adafruit-circuitpython-raspberry_pi_pico2_w-en_US-10.0.3.uf2"
SCRIPT_DIR = Path(__file__).resolve().parent
DEST_FILE = SCRIPT_DIR / "adafruit-circuitpython-raspberry_pi_pico2_w-en_US-10.0.3.uf2"


def main():
    if urllib.request is None:
        print("urllib が使えません。以下の URL から手動でダウンロードしてください:")
        print(UF2_URL)
        sys.exit(1)
    if DEST_FILE.exists():
        print(f"既に存在します: {DEST_FILE}")
        print_instructions(DEST_FILE)
        return
    print("CircuitPython UF2 をダウンロード中...")
    try:
        req = urllib.request.Request(UF2_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            DEST_FILE.write_bytes(resp.read())
        print(f"保存しました: {DEST_FILE}")
    except Exception as e:
        print(f"ダウンロード失敗: {e}")
        print("手動でダウンロード: " + UF2_URL)
        sys.exit(1)
    print_instructions(DEST_FILE)


def print_instructions(path: Path):
    print()
    print("=" * 60)
    print("次の手順で Pico 2 W に CircuitPython を入れましょう")
    print("=" * 60)
    print("1. Pico 2 W の BOOTSEL ボタンを押したまま USB ケーブルで接続する")
    print("2. PC に「RPI-RP2」などのドライブが表示されたら、次のファイルを")
    print("   そのドライブにコピー（ドラッグ＆ドロップ）する:")
    print()
    print(f"   {path}")
    print()
    print("3. コピーが終わると Pico が自動で再起動し、CIRCUITPY ドライブになる")
    print("4. その後、次のコマンドで code.py と adafruit_hid をコピーする:")
    print()
    print("   python pico_hid/copy_to_pico.py")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
