"""
ComfyUI-LTXVideo の gemma_encoder.py に model_root バグ修正を適用するスクリプト

原因: gemma_path がファイル（例: model-00001-of-00005.safetensors）のとき、
path.parents[1] が text_encoders になり、トークナイザーが親フォルダを参照して
「Unrecognized model in ... text_encoders」になる。

修正: model_root を Gemma モデルフォルダにする（path がファイルなら path.parent、そうでなければ path）。

使い方:
  set COMFYUI_PATH=C:\\ComfyUI
  python patch_ltxv_gemma_encoder.py
"""

import os
import shutil
import sys
from pathlib import Path

COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
GEMMA_ENCODER = COMFYUI_PATH / "custom_nodes" / "ComfyUI-LTXVideo" / "gemma_encoder.py"

OLD_LINE = "    model_root = path.parents[1]"
NEW_LINE = "    model_root = path.parent if path.is_file() else path"


def main():
    print("=" * 60)
    print("ComfyUI-LTXVideo gemma_encoder.py パッチ")
    print("=" * 60)
    print(f"対象: {GEMMA_ENCODER}")
    if not GEMMA_ENCODER.exists():
        print(
            "\n[ERR] ファイルが見つかりません。COMFYUI_PATH と ComfyUI-LTXVideo のインストールを確認してください。"
        )
        sys.exit(1)
    text = GEMMA_ENCODER.read_text(encoding="utf-8")
    if NEW_LINE in text:
        print("\n[OK] 既にパッチ適用済みです。")
        return
    if OLD_LINE not in text:
        print(
            "\n[WARN] 適用対象の行が見つかりません。gemma_encoder.py のバージョンが変わっている可能性があります。"
        )
        print(f"  探している行: {OLD_LINE!r}")
        sys.exit(1)
    backup = GEMMA_ENCODER.with_suffix(".gemma_encoder.py.bak")
    shutil.copy2(GEMMA_ENCODER, backup)
    print(f"\nバックアップ: {backup}")
    new_text = text.replace(OLD_LINE, NEW_LINE, 1)
    GEMMA_ENCODER.write_text(new_text, encoding="utf-8")
    print("[FIX] パッチを適用しました。")
    print("\nComfyUI を再起動してからワークフローを再実行してください。")
    print("=" * 60)


if __name__ == "__main__":
    main()
