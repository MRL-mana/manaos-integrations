#!/usr/bin/env python3
"""ComfyUI出力PNGからワークフローメタデータを抽出（最近の画像）"""
import sys, os, json, glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

try:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
except ImportError:
    print("Pillow not found, trying raw approach")

output_dir = Path(r"C:\ComfyUI\output")
# Get most recent PNGs (excluding our generated ones)
pngs = sorted(output_dir.glob("ComfyUI_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)

print(f"Total PNGs: {len(pngs)}")
print(f"Latest 5 (most recent first):")

# Skip our 3-4 most recent, look at older ones
skip_count = 5  # skip our recent generations
for i, png in enumerate(pngs[skip_count:skip_count+10]):
    print(f"\n=== {png.name} (modified: {png.stat().st_mtime}) ===")
    print(f"  Size: {png.stat().st_size} bytes")
    try:
        img = Image.open(png)  # type: ignore[possibly-unbound]
        print(f"  Dimensions: {img.size}")
        metadata = img.info
        if 'prompt' in metadata:
            wf = json.loads(metadata['prompt'])
            for nid, node in wf.items():
                ct = node.get('class_type', '')
                inp = node.get('inputs', {})
                if ct == 'CheckpointLoaderSimple':
                    print(f"  [Model] {inp.get('ckpt_name', '?')}")
                elif ct == 'CLIPTextEncode' and isinstance(inp.get('text'), str):
                    text = inp['text']
                    if len(text) > 200:
                        text = text[:200] + '...'
                    print(f"  [Text {nid}] {text}")
                elif ct == 'KSampler':
                    print(f"  [KSampler] sampler={inp.get('sampler_name')}, scheduler={inp.get('scheduler')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}")
                elif ct == 'LoraLoader':
                    print(f"  [LoRA] {inp.get('lora_name')}, str_model={inp.get('strength_model')}, str_clip={inp.get('strength_clip')}")
                elif ct == 'EmptyLatentImage':
                    print(f"  [Latent] {inp.get('width')}x{inp.get('height')}")
        elif 'workflow' in metadata:
            print("  Has 'workflow' metadata (ComfyUI format)")
            wf = json.loads(metadata['workflow'])
            for node in wf.get('nodes', []):
                wt = node.get('type', '')
                if wt in ('CheckpointLoaderSimple', 'KSampler', 'LoraLoader', 'CLIPTextEncode', 'EmptyLatentImage'):
                    print(f"  [{wt}] widgets: {node.get('widgets_values', [])}")
        else:
            print(f"  Metadata keys: {list(metadata.keys())}")
        img.close()
    except Exception as e:
        print(f"  Error reading: {e}")
