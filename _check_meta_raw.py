#!/usr/bin/env python3
"""PNG metadata raw dump for older images"""
import sys, os, json
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

output_dir = Path(r"C:\ComfyUI\output")

# Check specific older images 
targets = ['ComfyUI_06862_.png', 'ComfyUI_06861_.png', 'ComfyUI_06860_.png',
           'ComfyUI_06858_.png', 'ComfyUI_06850_.png', 'ComfyUI_06800_.png',
           'ComfyUI_06700_.png', 'ComfyUI_06600_.png', 'ComfyUI_06500_.png',
           'ComfyUI_06400_.png', 'ComfyUI_06300_.png', 'ComfyUI_06200_.png']

for name in targets:
    path = output_dir / name
    if not path.exists():
        continue
    try:
        img = Image.open(path)
        w, h = img.size
        print(f"\n=== {name} ({w}x{h}, {path.stat().st_size//1024}KB) ===")
        print(f"  Metadata keys: {list(img.info.keys())}")
        
        for key in img.info:
            val = img.info[key]
            if isinstance(val, str) and len(val) > 10:
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        for nid, node in parsed.items():
                            if isinstance(node, dict):
                                ct = node.get('class_type', '')
                                inp = node.get('inputs', {})
                                if ct == 'CheckpointLoaderSimple':
                                    print(f"  [Model] {inp.get('ckpt_name', '?')}")
                                elif ct == 'LoraLoader':
                                    print(f"  [LoRA] {inp.get('lora_name')}, str={inp.get('strength_model')}")
                                elif ct == 'KSampler':
                                    print(f"  [KSampler] sampler={inp.get('sampler_name')}, sched={inp.get('scheduler')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}")
                                elif ct == 'EmptyLatentImage':
                                    print(f"  [Latent] {inp.get('width')}x{inp.get('height')}")
                                elif ct == 'CLIPTextEncode' and isinstance(inp.get('text'), str):
                                    t = inp['text'][:200]
                                    print(f"  [Text {nid}] {t}")
                    elif isinstance(parsed, list):
                        print(f"  [{key}] list len={len(parsed)}")
                        if len(parsed) > 2 and isinstance(parsed[2], dict):
                            for nid, node in parsed[2].items():
                                if isinstance(node, dict):
                                    ct = node.get('class_type', '')
                                    inp = node.get('inputs', {})
                                    if ct == 'CheckpointLoaderSimple':
                                        print(f"    [Model] {inp.get('ckpt_name', '?')}")
                                    elif ct == 'LoraLoader':
                                        print(f"    [LoRA] {inp.get('lora_name')}, str={inp.get('strength_model')}")
                                    elif ct == 'KSampler':
                                        print(f"    [KSampler] sampler={inp.get('sampler_name')}, sched={inp.get('scheduler')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}")
                                    elif ct == 'EmptyLatentImage':
                                        print(f"    [Latent] {inp.get('width')}x{inp.get('height')}")
                                    elif ct == 'CLIPTextEncode' and isinstance(inp.get('text'), str):
                                        t = inp['text'][:200]
                                        print(f"    [Text {nid}] {t}")
                except json.JSONDecodeError:
                    print(f"  [{key}] (not JSON, len={len(val)}): {val[:100]}")
            elif isinstance(val, bytes):
                print(f"  [{key}] (bytes, len={len(val)})")
            else:
                print(f"  [{key}] {val}")
        img.close()
    except Exception as e:
        print(f"  Error: {e}")

# Also check subdirectories
print("\n\n=== Subdirectories in output ===")
for item in output_dir.iterdir():
    if item.is_dir():
        sub_files = list(item.glob("*.png"))
        print(f"  {item.name}/: {len(sub_files)} pngs")
        if sub_files:
            latest = sorted(sub_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
            print(f"    Latest: {latest.name} ({latest.stat().st_size//1024}KB)")
