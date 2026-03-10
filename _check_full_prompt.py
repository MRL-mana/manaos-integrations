#!/usr/bin/env python3
"""過去の生成で使われた完全なプロンプトを確認"""
import sys, json
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

output_dir = Path(r"C:\ComfyUI\output")

targets = [
    'ComfyUI_06700_.png',  # cyberrealisticPony + 2 LoRAs
    'ComfyUI_06600_.png',  # ponyDiffusion + majicMIX lux LoRA
    'ComfyUI_06500_.png',  # beautifulRealistic_v7 + cknb02 LoRA
    'ComfyUI_06400_.png',  # ponyDiffusion + FarrahMixer LoRA
]

for name in targets:
    path = output_dir / name
    if not path.exists():
        continue
    img = Image.open(path)
    print(f"\n{'='*60}")
    print(f"{name} ({img.size[0]}x{img.size[1]})")
    print(f"{'='*60}")
    
    raw = img.info.get('prompt', '')
    if raw:
        wf = json.loads(raw)
        if isinstance(wf, dict):
            for nid in sorted(wf.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                node = wf[nid]
                ct = node.get('class_type', '')
                inp = node.get('inputs', {})
                
                if ct == 'CheckpointLoaderSimple':
                    print(f"\n[{nid}] MODEL: {inp.get('ckpt_name')}")
                elif ct == 'LoraLoader':
                    print(f"[{nid}] LORA: name={inp.get('lora_name')}, strength_model={inp.get('strength_model')}, strength_clip={inp.get('strength_clip')}")
                elif ct == 'CLIPTextEncode':
                    text = inp.get('text', '')
                    label = 'POSITIVE' if text and not text.startswith('bad') else 'NEGATIVE'
                    print(f"[{nid}] {label}: {text}")
                elif ct == 'KSampler':
                    print(f"[{nid}] KSAMPLER: seed={inp.get('seed')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}, sampler={inp.get('sampler_name')}, scheduler={inp.get('scheduler')}, denoise={inp.get('denoise')}")
                elif ct == 'EmptyLatentImage':
                    print(f"[{nid}] LATENT: {inp.get('width')}x{inp.get('height')} batch={inp.get('batch_size')}")
                elif ct == 'VAEDecode':
                    pass
                elif ct == 'SaveImage':
                    print(f"[{nid}] SAVE: prefix={inp.get('filename_prefix')}")
                else:
                    print(f"[{nid}] {ct}: {json.dumps(inp, ensure_ascii=False)[:200]}")
    img.close()
