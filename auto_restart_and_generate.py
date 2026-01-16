#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI起動待機と画像生成を自動実行"""

import requests
import time
import sys
import io
import subprocess
import random
import hashlib

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
GALLERY_API = "http://localhost:5559/api/generate"

print("=" * 60)
print("ComfyUI起動待機と画像生成")
print("=" * 60)
print()

# 1. ComfyUI起動を待つ
print("1. ComfyUIの起動を待機中...")
max_wait = 120  # 最大2分待機
waited = 0
comfyui_ready = False

while waited < max_wait:
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        if response.status_code == 200:
            comfyui_ready = True
            print("   [OK] ComfyUI起動確認")
            break
    except:
        pass
    
    if waited % 10 == 0 and waited > 0:
        print(f"   待機中... ({waited}秒経過)")
    
    time.sleep(2)
    waited += 2

if not comfyui_ready:
    print("   [ERROR] ComfyUIが起動しませんでした")
    print("   手動でComfyUIを起動してください:")
    print("     .\\start_comfyui_simple.bat")
    sys.exit(1)

print()

# 2. 画像生成を実行
print("2. 画像生成を実行中...")
print()

job_ids = []
models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosa25D_v12.safetensors",
    "speciosaRealistica_v12b.safetensors",
    "uwazumimixILL_v50.safetensors",
    "shibari_v20.safetensors"
]

expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes", "large eyes", "innocent eyes"]
faces = ["beautiful face", "perfect face", "refined face", "cute face", "neat face", "well-defined face", "pretty face"]
bodies = ["toned body", "fit body", "athletic body", "slim body", "tight body", "well-proportioned body", "curvy body"]
poses = ["cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl", "sitting", "lying down"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment", "romantic scene"]
hair_styles = ["long hair", "short hair", "wavy hair", "straight hair", "curly hair", "ponytail", "twintails"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting", "studio lighting", "ambient light"]
backgrounds = ["bedroom", "bed", "hotel room", "intimate setting", "private room", "romantic atmosphere"]

for i in range(10):
    model = random.choice(models)
    
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        random.choice(hair_styles),
        random.choice(lighting),
        random.choice(backgrounds),
        "high quality", "masterpiece", "best quality", "perfect anatomy", "correct anatomy",
        "detailed", "sharp focus", "8k uhd", "photorealistic"
    ]
    prompt = ", ".join(prompt_parts)
    
    # パラメータ
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        steps = random.choice([45, 50, 55, 60])
        width, height = random.choice([(768, 1024), (1024, 768), (832, 1216), (896, 1152)])
    
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras", "exponential"])
    
    # Seed生成
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
    
    print(f"[{i+1}/10] モデル: {model}")
    print(f"  プロンプト: {prompt[:80]}...")
    print(f"  解像度: {width}x{height}, ステップ: {steps}, CFG: {guidance_scale}, Seed: {seed}")
    
    try:
        response = requests.post(
            GALLERY_API,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                prompt_id = result.get("prompt_id")
                job_ids.append((job_id, prompt_id, model))
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [HTTP ERROR] {response.status_code}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    if i < 9:
        time.sleep(1)

print()
print("=" * 60)
print(f"[完了] {len(job_ids)}件の画像生成ジョブを送信しました")
print("=" * 60)
print()

if len(job_ids) > 0:
    print("ジョブID一覧:")
    for i, (job_id, prompt_id, model) in enumerate(job_ids, 1):
        print(f"  {i}. {job_id} ({model})")
    print()
    print("画像生成の進行状況を確認中...")
    print()
    
    # 少し待ってから状態確認
    time.sleep(15)
    
    success_count = 0
    error_count = 0
    pending_count = 0
    
    for job_id, prompt_id, model in job_ids:
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    data = history[prompt_id]
                    status = data.get("status", {})
                    status_str = status.get("status_str", "unknown")
                    outputs = data.get("outputs", {})
                    has_images = any("images" in node_output for node_output in outputs.values())
                    
                    if status_str == "success" and has_images:
                        success_count += 1
                    elif status_str == "error":
                        error_count += 1
                    else:
                        pending_count += 1
        except:
            pending_count += 1
    
    print(f"生成状況: 成功 {success_count}件, エラー {error_count}件, 処理中 {pending_count}件")
    print()
    print("画像生成の進行状況は以下で確認できます:")
    print("  http://localhost:5559/api/images")
    print()
    print("詳細確認:")
    print("  python check_all_recent_jobs.py")
