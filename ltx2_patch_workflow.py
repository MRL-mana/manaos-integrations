#!/usr/bin/env python3
"""
API形式ワークフローを現在のComfyUIノード名に合わせてパッチする。
- CM_FloatToInt -> PrimitiveInt (value=8)
- LTXVAudioVAELoader -> LowVRAMAudioVAELoader (ckpt_name)
※ サブグラフ(UUID)ノードはComfyUI UIでワークフローを開き「Export (API)」すると展開されます。
"""
import json
import sys
from pathlib import Path

# ノード名の置換（既存inputsは維持し、不足分だけデフォルトを入れる）
# 旧 ComfyUI-LTXVideo ノード名 -> 現行ノード名
NODE_REPLACEMENTS = {
    "CM_FloatToInt": ("PrimitiveInt", {"value": 8}),
    "LTXVAudioVAELoader": (
        "LowVRAMAudioVAELoader",
        {"ckpt_name": "ltx-2-19b-distilled.safetensors"},
    ),
    "LTXVImgToVideoInplace": ("LTXVImgToVideo", {}),
    "LTXVEmptyLatentAudio": ("EmptyLTXVLatentVideo", {}),
    "LTXVAudioVAEDecode": ("LTXVSpatioTemporalTiledVAEDecode", {}),
    "LTXVConcatAVLatent": ("LTXVAddLatents", {}),
    "LTXVSeparateAVLatent": ("LTXVSelectLatents", {}),
    "LTXVLatentUpsampler": ("LowVRAMLatentUpscaleModelLoader", {}),
}


# 出力に含めないノード（他から参照されないノート等）
SKIP_NODE_TYPES = {"MarkdownNote"}


def patch_workflow(api: dict) -> dict:
    out = {}
    for nid, node in api.items():
        if not isinstance(node, dict) or "class_type" not in node:
            continue
        ct = node["class_type"]
        if ct in SKIP_NODE_TYPES:
            continue
        if ct in NODE_REPLACEMENTS:
            new_ct, default_inputs = NODE_REPLACEMENTS[ct]
            inp = dict(node.get("inputs", {}))
            for k, v in default_inputs.items():
                if k not in inp:
                    inp[k] = v
            out[nid] = {"class_type": new_ct, "inputs": inp}
        else:
            out[nid] = node
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: ltx2_patch_workflow.py <api_workflow.json> [out.json]", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        print("", file=sys.stderr)
        print("To create ltx2_i2v_from_ui.json:", file=sys.stderr)
        print("  1. Open ComfyUI in browser: http://127.0.0.1:8188", file=sys.stderr)
        print(
            "  2. Load: ComfyUI-LTXVideo/example_workflows/LTX-2_I2V_Distilled_wLora.json",
            file=sys.stderr,
        )
        print(
            "  3. File -> Export (API), save as ltx2_workflows/ltx2_i2v_from_ui.json",
            file=sys.stderr,
        )
        return 1
    out_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else path.with_name(path.stem + "_patched.json")
    )
    if not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8") as f:
        api = json.load(f)
    patched = patch_workflow(api)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(patched, f, indent=2, ensure_ascii=False)
    print("Wrote", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
