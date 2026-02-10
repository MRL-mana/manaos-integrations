#!/usr/bin/env python3
"""
Pico 2 W の CIRCUITPY ドライブに code.py と adafruit_hid をコピーする。
Pico を USB で接続し、CircuitPython で CIRCUITPY がマウントされている状態で実行する。
"""

import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import urllib.request

    _has_urllib = True
except ImportError:
    _has_urllib = False

REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_PY_SRC = REPO_ROOT / "pico_hid" / "circuitpython" / "code.py"
BUNDLE_RELEASES_LATEST = "https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/latest"


def get_bundle_download_urls():
    """10.x-mpy バンドル ZIP の URL を、試す順で列挙する。"""
    # releases/latest にアクセスすると tag/YYYYMMDD にリダイレクトされる
    try:
        req = urllib.request.Request(
            BUNDLE_RELEASES_LATEST,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.geturl()
        tag = final_url.rstrip("/").split("/")[-1]
        yield (
            "https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases"
            f"/download/{tag}/adafruit-circuitpython-bundle-10.x-mpy-{tag}.zip"
        )
    except Exception:
        pass
    # フォールバック: 実際のリリースタグ（YYYYMMDD）
    for date in ("20250429", "20240430", "20240615"):
        yield (
            "https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases"
            f"/download/{date}/adafruit-circuitpython-bundle-10.x-mpy-{date}.zip"
        )


def find_circuitpy_drive():
    """Windows で CIRCUITPY ドライブを探す（boot_out.txt があるドライブ）。"""
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        root = Path(f"{letter}:")
        if not root.exists():
            continue
        boot_out = root / "boot_out.txt"
        if boot_out.is_file():
            return str(root)
        # ボリュームラベルで CIRCUITPY を探す（オプション）
        try:
            if os.path.exists(root / "code.py") or os.path.exists(root / "lib"):
                # boot_out.txt がなくても code.py や lib があれば CircuitPython の可能性
                if (root / "boot_out.txt").exists() or (root / "CIRCUITPY").exists():
                    return str(root)
        except OSError:
            pass
    return None


def ensure_adafruit_hid(circuitpy_root: Path) -> bool:
    """CIRCUITPY の lib に adafruit_hid があるか確認。なければバンドルから取得。"""
    import tempfile

    lib_dir = circuitpy_root / "lib"
    hid_dir = lib_dir / "adafruit_hid"
    if hid_dir.is_dir() and any(hid_dir.iterdir()):
        print("lib/adafruit_hid は既にあります。")
        return True
    if not _has_urllib:
        print("urllib が使えません。adafruit_hid を手動でコピーしてください。")
        return False
    lib_dir.mkdir(parents=True, exist_ok=True)
    last_error = None
    for bundle_url in get_bundle_download_urls():
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "bundle.zip"
            try:
                req = urllib.request.Request(bundle_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    zip_path.write_bytes(resp.read())
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for name in zf.namelist():
                        norm = name.replace("\\", "/")
                        if "adafruit_hid" in norm and (norm.endswith(".py") or "/" in norm):
                            zf.extract(name, tmp_path)
                # 解凍後: バンドルは xxx/lib/adafruit_hid/ の形
                src_hid = None
                for d in tmp_path.iterdir():
                    if d.is_dir():
                        cand = d / "lib" / "adafruit_hid"
                        if cand.exists():
                            src_hid = cand
                            break
                if src_hid is None and (tmp_path / "lib" / "adafruit_hid").exists():
                    src_hid = tmp_path / "lib" / "adafruit_hid"
                if src_hid is not None:
                    dest = lib_dir / "adafruit_hid"
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(src_hid, dest)
                    print("lib/adafruit_hid をコピーしました。")
                    return True
            except Exception as e:
                last_error = e
                continue
    if last_error:
        print(f"adafruit_hid の取得に失敗: {last_error}")
    return False


def main():
    circuitpy = find_circuitpy_drive()
    if not circuitpy:
        print("CIRCUITPY ドライブが見つかりません。")
        print(
            "Pico 2 W を USB で接続し、CircuitPython で CIRCUITPY がマウントされているか確認してください。"
        )
        sys.exit(1)
    root = Path(circuitpy)
    print(f"CIRCUITPY: {root}")

    if not CODE_PY_SRC.is_file():
        print(f"code.py が見つかりません: {CODE_PY_SRC}")
        sys.exit(1)
    shutil.copy2(CODE_PY_SRC, root / "code.py")
    print("code.py をコピーしました。")

    if not ensure_adafruit_hid(root):
        print("adafruit_hid は手動でコピーしてください: https://circuitpython.org/libraries")
        sys.exit(1)
    print("完了しました。")


if __name__ == "__main__":
    main()
