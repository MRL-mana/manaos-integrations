#!/usr/bin/env python3
"""大きなサイズの画像（実際の生成物）のメタデータを確認"""
import sys, os, json
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

output_dir = Path(r"C:\ComfyUI\output")
pngs = sorted(output_dir.glob("ComfyUI_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)

print(f"Total PNGs: {len(pngs)}")

# Find large images (actual generations, not 64x64)
count = 0
for png in pngs:
    if png.stat().st_size < 50000:
        continue
    try:
        img = Image.open(png)
        w, h = img.size
        if w < 200 or h < 200:
            img.close()
            continue
        
        count += 1
        print(f"\n=== {png.name} ({w}x{h}, {png.stat().st_size//1024}KB) ===")
        
        metadata = img.info
        if 'prompt' in metadata:
            raw = metadata['prompt']
            wf = json.loads(raw)
            if isinstance(wf, list):
                # ComfyUI prompt format: [number, prompt_id, workflow_dict, ...]
                if len(wf) > 2 and isinstance(wf[2], dict):
                    wf = wf[2]
                else:
                    print(f"  Prompt is a list of len {len(wf)}")
                    wf = {}
            if isinstance(wf, dict):
                for nid, node in wf.items():
                    ct = node.get('class_type', '')
                    inp = node.get('inputs', {})
                    if ct == 'CheckpointLoaderSimple':
                        print(f"  [Model] {inp.get('ckpt_name', '?')}")
                    elif ct in ('CLIPTextEncode', 'BNK_CLIPTextEncodeAdvanced') and isinstance(inp.get('text'), str):
                        text = inp['text']
                        if len(text) > 250:
                            text = text[:250] + '...'
                        print(f"  [Text {nid}] {text}")
                    elif ct == 'KSampler' or ct == 'KSamplerAdvanced':
                        print(f"  [KSampler] sampler={inp.get('sampler_name')}, scheduler={inp.get('scheduler')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}")
                    elif ct == 'LoraLoader' or ct == 'LoraLoaderModelOnly':
                        print(f"  [LoRA] {inp.get('lora_name')}, str={inp.get('strength_model')}")
                    elif ct == 'EmptyLatentImage':
                        print(f"  [Latent] {inp.get('width')}x{inp.get('height')}")
        
        if 'workflow' in metadata:
            wf2 = json.loads(metadata['workflow'])
            nodes = wf2.get('nodes', [])
            for node in nodes:
                wt = node.get('type', '')
                wv = node.get('widgets_values', [])
                if wt == 'CheckpointLoaderSimple' and wv:
                    print(f"  [WF Model] {wv}")
                elif wt in ('LoraLoader', 'LoraLoaderModelOnly') and wv:
                    print(f"  [WF LoRA] {wv}")
        
        img.close()
        
        if count >= 8:
            break
    except Exception as e:
        print(f"  Error: {e}")

if count == 0:
    print("No large images found in recent output!")
    # Check subdirectories
    for subdir in output_dir.iterdir():
        if subdir.is_dir():
            sub_pngs = list(subdir.glob("*.png"))
            print(f"  Subdir {subdir.name}: {len(sub_pngs)} pngs")
