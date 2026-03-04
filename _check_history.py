#!/usr/bin/env python3
"""ComfyUI過去ワークフロー解析"""
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

r = requests.get('http://127.0.0.1:8188/history', timeout=10)
data = r.json()
print(f"Total history entries: {len(data)}")

our_ids = [
    '3e364649-a604-4648-8864-6ac06d183508',
    'f6a8da6b-aa91-40ab-ae45-843645b8eb39',
    'e99cf618-329a-4e7d-88e1-e13474852c17',
]
entries = [(pid, v) for pid, v in data.items() if pid not in our_ids]
print(f"Previous entries (excluding ours): {len(entries)}")

for pid, v in entries[:15]:
    prompt_info = v.get('prompt', [])
    outputs = v.get('outputs', {})
    status = v.get('status', {})
    workflow = prompt_info[2] if len(prompt_info) > 2 else {}

    print(f"\n=== {pid} ===")
    print(f"  Status: {status.get('status_str', '?')}")

    for nid, node in workflow.items():
        ct = node.get('class_type', '')
        inp = node.get('inputs', {})
        if ct == 'CheckpointLoaderSimple':
            print(f"  [Model] {inp.get('ckpt_name', '?')}")
        elif ct == 'CLIPTextEncode' and 'text' in inp:
            text = inp['text']
            if len(text) > 150:
                text = text[:150] + '...'
            print(f"  [Text node {nid}] {text}")
        elif ct == 'KSampler':
            print(f"  [KSampler] sampler={inp.get('sampler_name')}, scheduler={inp.get('scheduler')}, steps={inp.get('steps')}, cfg={inp.get('cfg')}, seed={inp.get('seed')}")
        elif ct == 'LoraLoader':
            print(f"  [LoRA] {inp.get('lora_name')}, strength_model={inp.get('strength_model')}, strength_clip={inp.get('strength_clip')}")
        elif ct == 'EmptyLatentImage':
            print(f"  [Size] {inp.get('width')}x{inp.get('height')}")

    for nid, out in outputs.items():
        for img in out.get('images', []):
            print(f"  [Output] {img.get('filename', '?')} subfolder={img.get('subfolder', '')}")
