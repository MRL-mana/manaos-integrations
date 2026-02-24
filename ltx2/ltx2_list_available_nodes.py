#!/usr/bin/env python3
"""
ComfyUI の /object_info から取得したノード一覧のうち、
LTX-2 / 動画まわりで使うノード名だけを表示します。

使い方:
  ComfyUI を起動した状態で:
    python ltx2_list_available_nodes.py
  オプション:
    --comfy-url URL   ComfyUIのURL（既定: http://127.0.0.1:8188）
    --all             全ノードを表示（フィルタなし）
"""
import argparse
import os
import sys

import requests

from _paths import COMFYUI_PORT

COMFYUI_URL_DEFAULT = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")

# LTX / 動画で使うノードのプレフィックス・キーワード
RELEVANT_KEYWORDS = (
    "LTXV",
    "LTX ",
    "LowVRAM",
    "SaveVideo",
    "CreateVideo",
    "VAEDecode",
    "VAE",
    "Latent",
    "Video",
    "Audio",
)


def get_object_info(base_url: str) -> dict | None:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"ComfyUIに接続できません: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="ComfyUIで利用可能なLTX/動画関連ノード一覧を表示")
    parser.add_argument(
        "--comfy-url",
        default=os.environ.get("COMFYUI_URL", COMFYUI_URL_DEFAULT),
        help="ComfyUIのURL",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全ノードを表示（フィルタなし）",
    )
    args = parser.parse_args()

    obj = get_object_info(args.comfy_url)
    if obj is None:
        sys.exit(1)

    names = sorted(obj.keys())
    if args.all:
        for n in names:
            print(n)
        print(f"\n合計: {len(names)} ノード")
        return

    relevant = [n for n in names if any(kw in n for kw in RELEVANT_KEYWORDS)]
    print("=" * 60)
    print("ComfyUI で利用可能な LTX / 動画関連ノード")
    print("=" * 60)
    print(f"URL: {args.comfy_url}")
    print(f"該当ノード数: {len(relevant)}")
    print()
    for n in relevant:
        print(f"  {n}")
    print()
    print("上記ノードだけを使ったワークフローなら「node XXX does not exist」を避けられます。")
    print(
        "互換ワークフローを探す: python ltx2_find_compatible_workflow.py <example_workflowsのパス>"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
