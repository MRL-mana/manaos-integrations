#!/usr/bin/env python3
"""
指定フォルダ内のワークフロー JSON を走査し、
現在の ComfyUI（/object_info）に存在するノードだけを使っているものを表示します。

使い方:
  ComfyUI を起動した状態で:
    python ltx2_find_compatible_workflow.py \\
      "C:\\ComfyUI\\custom_nodes\\ComfyUI-LTXVideo\\example_workflows"
  オプション:
    --comfy-url URL   ComfyUIのURL（既定: http://127.0.0.1:8188）
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

COMFYUI_URL_DEFAULT = "http://127.0.0.1:8188"


def get_object_info(base_url: str) -> dict | None:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"ComfyUIに接続できません: {e}", file=sys.stderr)
        return None


def collect_class_types(workflow: dict) -> set[str]:
    """API形式のワークフローから class_type を集める"""
    out = set()
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "class_type" in node:
            out.add(node["class_type"])
    return out


def main():
    parser = argparse.ArgumentParser(
        description="example_workflows 内で、現在のComfyUIと互換のワークフローを検出"
    )
    parser.add_argument(
        "workflows_dir",
        nargs="?",
        default=None,
        help="example_workflows フォルダのパス（未指定時はよくあるパスを試す）",
    )
    parser.add_argument(
        "--comfy-url",
        default=os.environ.get("COMFYUI_URL", COMFYUI_URL_DEFAULT),
        help="ComfyUIのURL",
    )
    args = parser.parse_args()

    obj = get_object_info(args.comfy_url)
    if obj is None:
        sys.exit(1)
    available = set(obj.keys())

    candidates = [
        Path(args.workflows_dir) if args.workflows_dir else None,
        Path("C:/ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows"),
        Path(__file__).resolve().parent / "ltx2_workflows",
    ]
    base = None
    for p in candidates:
        if p and p.is_dir():
            base = p
            break
    if base is None:
        print("ワークフロー用フォルダが見つかりません。", file=sys.stderr)
        cmd = 'ltx2_find_compatible_workflow.py "...\\ComfyUI-LTXVideo\\example_workflows"'
        print(f"  python {cmd}", file=sys.stderr)
        sys.exit(1)

    json_files = list(base.glob("**/*.json"))
    if not json_files:
        print(f"JSONが1件もありません: {base}", file=sys.stderr)
        sys.exit(1)

    compatible = []
    for path in sorted(json_files):
        try:
            with open(path, "r", encoding="utf-8") as f:
                w = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [スキップ] {path.name}: {e}", file=sys.stderr)
            continue
        types_in_workflow = collect_class_types(w)
        missing = types_in_workflow - available
        if not missing:
            compatible.append((path, types_in_workflow))
        else:
            miss_preview = sorted(missing)[:5]
            suffix = " ..." if len(missing) > 5 else ""
            print(f"  [不足あり] {path.name}: {miss_preview}{suffix}")

    print("=" * 60)
    print("現在のComfyUIと互換のワークフロー")
    print("=" * 60)
    print(f"ComfyUI: {args.comfy_url}")
    print(f"対象フォルダ: {base}")
    print()
    if not compatible:
        print("互換のワークフローはありません。")
        print("  - ltx2_list_available_nodes.py で利用可能ノードを確認")
        print("  - ComfyUI-LTXVideo のバージョン（別ブランチ/過去コミット）を試す")
        print("  - https://github.com/Lightricks/ComfyUI-LTXVideo/issues で情報を確認")
    else:
        for path, types_ in compatible:
            print(f"  [互換] {path}")
        print()
        print("上記のいずれかを ComfyUI で開き、File -> Export (API) で保存してから")
        print("  上記を Export (API) で保存し、run_ltx2_generate.py --workflow で実行可。")
    print("=" * 60)


if __name__ == "__main__":
    main()
