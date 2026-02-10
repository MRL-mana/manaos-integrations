#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gallery APIを強制再起動して画像生成"""

import requests
import time
import sys
import io
import random
import hashlib
import subprocess
import os

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
GALLERY_API = "http://localhost:5559/api/generate"

print("=" * 60)
print("Gallery API強制再起動と画像生成")
print("=" * 60)
print()

# 1. ComfyUI確認
print("1. ComfyUI確認:")
try:
    response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
    if response.status_code == 200:
        print("   [OK] ComfyUI起動中")
    else:
        print(f"   [WARN] ComfyUI応答異常: {response.status_code}")
except Exception:
    print("   [ERROR] ComfyUIに接続できません")
    sys.exit(1)

print()

# 2. Gallery API確認と再起動案内
print("2. Gallery API確認:")
try:
    response = requests.get("http://localhost:5559/api/images", timeout=2)
    if response.status_code == 200:
        print("   [OK] Gallery API起動中")
        print("   注意: モデル検索エラーが発生している可能性があります")
        print("   Gallery APIを再起動してください")
except Exception:
    print("   [WARN] Gallery APIに接続できません")

print()

# 3. 直接ComfyUIに送信を試行
print("3. 直接ComfyUIに画像生成を送信...")
print()

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
prompt_ids = []

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
    
    # Gallery API経由で送信を試行
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
                prompt_id = result.get("prompt_id")
                job_ids.append(job_id)
                prompt_ids.append(prompt_id)
                print(f"  [OK] {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown')}")
        else:
            print(f"  [HTTP {response.status_code}]")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    time.sleep(1)

print()
print("=" * 60)
print(f"送信完了: {len(job_ids)}件")
print("=" * 60)

if len(job_ids) > 0:
    print()
    print("ジョブID一覧:")
    for i, (job_id, prompt_id) in enumerate(zip(job_ids, prompt_ids), 1):
        print(f"  {i}. {job_id}")
    print()
    print("画像生成の進行状況を確認中...")
    time.sleep(20)
    
    success_count = 0
    for prompt_id in prompt_ids:
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    data = history[prompt_id]
                    status = data.get("status", {})
                    status_str = status.get("status_str", "unknown")
                    if status_str == "success":
                        success_count += 1
        except Exception:
            pass
    
    print(f"生成状況: 成功 {success_count}件 / {len(prompt_ids)}件")
    print()
    print("詳細確認:")
    print("  python check_all_recent_jobs.py")
