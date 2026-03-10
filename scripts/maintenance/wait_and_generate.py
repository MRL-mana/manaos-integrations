#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI起動を待って画像生成"""

import requests
import time
import sys
import io
import random
import hashlib

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

from _paths import COMFYUI_PORT, GALLERY_PORT

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")  # type: ignore[name-defined]
GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/generate"  # type: ignore[name-defined]

print("=" * 60)
print("ComfyUI起動待機と画像生成")
print("=" * 60)
print()

# ComfyUI起動を待つ（最大60秒）
print("ComfyUIの起動を待機中...")
for i in range(30):
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        if response.status_code == 200:
            print("[OK] ComfyUI起動確認")
            break
    except Exception:
        pass
    
    if i % 5 == 0 and i > 0:
        print(f"待機中... ({i*2}秒)")
    time.sleep(2)
else:
    print("[WARN] ComfyUIが起動していません。生成を試行します...")

print()

# 画像生成
models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosa25D_v12.safetensors",
    "speciosaRealistica_v12b.safetensors",
    "uwazumimixILL_v50.safetensors",
    "shibari_v20.safetensors"
]

expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes"]
faces = ["beautiful face", "perfect face", "refined face", "cute face", "well-defined face"]
bodies = ["toned body", "fit body", "athletic body", "slim body", "tight body"]
poses = ["cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex"]

job_ids = []

for i in range(10):
    model = random.choice(models)
    
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        "high quality", "masterpiece", "best quality", "perfect anatomy"
    ]
    prompt = ", ".join(prompt_parts)
    
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60])
        width, height = random.choice([(1024, 1024), (1024, 1280)])
    else:
        steps = random.choice([45, 50, 55])
        width, height = random.choice([(768, 1024), (1024, 768), (832, 1216)])
    
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2"])
    scheduler = random.choice(["normal", "karras"])
    
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    seed = (time_seed ^ random_seed ^ model_hash ^ prompt_hash ^ i) % (2**32)
    
    payload = {
        "prompt": prompt,
        "model": model,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "width": width,
        "height": height,
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": seed,
        "mufufu_mode": True
    }
    
    print(f"[{i+1}/10] {model}")
    print(f"  {prompt[:60]}...")
    
    try:
        response = requests.post(GALLERY_API, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                job_ids.append(job_id)
                print(f"  [OK] {job_id}")
            else:
                print(f"  [ERROR] {result.get('error')}")
        else:
            print(f"  [HTTP {response.status_code}]")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    time.sleep(1)

print()
print("=" * 60)
print(f"送信完了: {len(job_ids)}件")
print("=" * 60)
