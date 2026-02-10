"""
ComfyUI-LTXVideo の gemma_encoder.py をパッチするスクリプト

原因: gemma_path がファイル（例: model-00001-of-00005.safetensors）のとき、
      path.parents[1] が text_encoders になり、トークナイザーが親フォルダを参照して
      "Unrecognized model in ... text_encoders" になる。

修正: model_root を Gemma モデルフォルダにする
      model_root = path.parents[1]  →  model_root = path.parent if path.is_file() else path

使い方:
  set COMFYUI_PATH=C:\\ComfyUI
  python patch_ltxv_gemma_path.py
"""

import os
import sys
from pathlib import Path

COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
GEMMA_ENCODER = COMFYUI_PATH / "custom_nodes" / "ComfyUI-LTXVideo" / "gemma_encoder.py"

OLD_LINE = "    model_root = path.parents[1]"
NEW_LINE = "    model_root = path.parent if path.is_file() else path  # LTX: use gemma folder, not text_encoders"


def main():
    print("=" * 60)
    print("ComfyUI-LTXVideo gemma_encoder.py パッチ")
    print("=" * 60)
    print(f"対象: {GEMMA_ENCODER}")
    if not GEMMA_ENCODER.exists():
        print("\n[ERR] ファイルがありません。COMFYUI_PATH を確認してください。")
        sys.exit(1)
    text = GEMMA_ENCODER.read_text(encoding="utf-8")
    if NEW_LINE in text:
        print("\n[OK] 既にパッチ済みです。")
        return
    if OLD_LINE not in text:
        print("\n[WARN] パッチ対象の行が見つかりません。ComfyUI-LTXVideo のバージョンが変わっている可能性があります。")
        print(f"  探した行: {OLD_LINE!r}")
        sys.exit(1)
    new_text = text.replace(OLD_LINE, NEW_LINE, 1)
    GEMMA_ENCODER.write_text(new_text, encoding="utf-8")
    print("\n[FIX] パッチを適用しました。ComfyUI を再起動してください。")
    print("=" * 60)


if __name__ == "__main__":
    main()
