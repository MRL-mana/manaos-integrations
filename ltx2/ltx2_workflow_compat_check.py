"""
現在のComfyUIに、LTX-2 I2Vワークフローで必要なノードが揃っているか確認するスクリプト。

不足ノードがある場合、現在のComfyUI-LTXVideoのバージョンと
ワークフロー（LTX-2_I2V_Distilled_wLora 等）のバージョンが一致していません。
"""

import sys
import requests

from _paths import COMFYUI_PORT

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")  # type: ignore[name-defined]

# I2Vワークフローでよく使うノード（すべて必須ではないが、ltx2_i2v_from_ui 系で参照される）
REQUIRED_FOR_I2V = [
    "LTXVGemmaCLIPModelLoader",
    "LowVRAMAudioVAELoader",
    "LTXVEmptyLatentAudio",
    "LTXVImgToVideoInplace",
    "LTXVSeparateAVLatent",
    "LTXVSpatioTemporalTiledVAEDecode",
    "LTXVAudioVAEDecode",
    "LTXVLatentUpsampler",
    "LTXVConcatAVLatent",
    "SaveVideo",
    "CreateVideo",
]


def main():
    try:
        r = requests.get(f"{COMFYUI_URL}/object_info", timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"ComfyUIに接続できません: {e}")
        print(f"  URL: {COMFYUI_URL}")
        sys.exit(1)

    nodes = r.json()
    missing = [n for n in REQUIRED_FOR_I2V if n not in nodes]
    present = [n for n in REQUIRED_FOR_I2V if n in nodes]

    print("=" * 60)
    print("LTX-2 I2V ワークフロー 互換性チェック")
    print("=" * 60)
    print(f"ComfyUI: {COMFYUI_URL}")
    print(f"必要なノードのうち {len(present)}/{len(REQUIRED_FOR_I2V)} が存在します。")
    print()
    for n in present:
        print(f"  [OK] {n}")
    for n in missing:
        print(f"  [不足] {n}")

    if not missing:
        print()
        print("この環境では ltx2_i2v_from_ui.json 等のワークフローが実行できる可能性があります。")
        sys.exit(0)

    print()
    print("【対処】")
    print("  現在のComfyUI-LTXVideoには上記ノードがありません。")
    print("  1) 利用可能なノード一覧を確認:")
    print("       python ltx2_list_available_nodes.py")
    print("  2) example_workflows 内で互換のワークフローを自動検出:")
    print(
        '       python ltx2_find_compatible_workflow.py "C:\\ComfyUI\\custom_nodes\\ComfyUI-LTXVideo\\example_workflows"'
    )
    print("  3) 互換ワークフローがあれば、ComfyUIで開き File -> Export (API) で保存し、")
    print("     run_ltx2_generate.py --workflow そのファイル で実行する。")
    print(
        "  4) 互換がなければ ComfyUI-LTXVideo のバージョン変更（別ブランチ／過去コミット）を検討。"
    )
    print("=" * 60)
    sys.exit(1)


if __name__ == "__main__":
    main()
