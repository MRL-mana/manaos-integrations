#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加で30枚の画像を生成"""

import requests
import json
import time
import sys
import io
import random
import hashlib

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"

# 成功したモデルのみ使用
models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosa25D_v12.safetensors",
    "uwazumimixILL_v50.safetensors"
]

MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure"

def create_workflow(prompt, negative_prompt, model, steps, guidance_scale, width, height, sampler, scheduler, seed):
    """ComfyUIワークフローを作成"""
    workflow = {
        "1": {
            "inputs": {"ckpt_name": model},
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {"text": prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {"text": negative_prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode"
        },
        "4": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": guidance_scale,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {"filename_prefix": "ComfyUI", "images": ["6", 0]},
            "class_type": "SaveImage"
        }
    }
    return workflow

print("=" * 60)
print("追加で30枚の画像生成")
print("=" * 60)
print()

expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes", "large eyes", "innocent eyes", "beautiful eyes"]
faces = ["beautiful face", "perfect face", "refined face", "cute face", "well-defined face", "pretty face", "attractive face", "lovely face"]
bodies = ["toned body", "fit body", "athletic body", "slim body", "tight body", "curvy body", "well-proportioned body", "sexy body"]
poses = ["cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl", "sitting", "lying down", "standing"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment", "romantic scene", "erotic scene"]
hair_styles = ["long hair", "short hair", "wavy hair", "straight hair", "curly hair", "ponytail", "twintails", "bob cut"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting", "studio lighting", "ambient light", "romantic lighting"]
backgrounds = ["bedroom", "bed", "hotel room", "intimate setting", "private room", "romantic atmosphere", "luxury room"]

prompt_ids = []

for i in range(30):
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
        "detailed", "sharp focus", "8k uhd", "photorealistic", "ultra detailed"
    ]
    prompt = ", ".join(prompt_parts)
    
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024), (1152, 896)])
    else:
        steps = random.choice([45, 50, 55, 60])
        width, height = random.choice([(768, 1024), (1024, 768), (832, 1216), (896, 1152), (960, 1280)])
    
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras", "exponential"])
    
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    seed = (time_seed ^ random_seed ^ model_hash ^ prompt_hash ^ i) % (2**32)
    
    workflow = create_workflow(
        prompt=prompt,
        negative_prompt=MUFUFU_NEGATIVE_PROMPT,
        model=model,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed
    )
    
    print(f"[{i+1:2d}/30] {model}")
    print(f"  {prompt[:70]}...")
    print(f"  {width}x{height}, {steps}steps, CFG:{guidance_scale}, Seed:{seed}")
    
    try:
        payload = {"prompt": workflow}
        response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            if prompt_id:
                prompt_ids.append(prompt_id)
                print(f"  [OK] {prompt_id}")
            else:
                print(f"  [ERROR] プロンプトIDが返されませんでした")
        else:
            print(f"  [HTTP {response.status_code}]")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    # 送信間隔を調整（ComfyUIの負荷を考慮）
    if i < 29:
        time.sleep(0.5)

print()
print("=" * 60)
print(f"送信完了: {len(prompt_ids)}件")
print("=" * 60)

if len(prompt_ids) > 0:
    print()
    print("プロンプトID一覧:")
    for i, prompt_id in enumerate(prompt_ids, 1):
        if i % 10 == 0 or i == len(prompt_ids):
            print(f"  {i:2d}. {prompt_id}")
        elif i <= 5 or i > len(prompt_ids) - 5:
            print(f"  {i:2d}. {prompt_id}")
    
    print()
    print("画像生成の進行状況を確認中...")
    print("（生成には時間がかかります）")
    print()
    print("生成状況の確認:")
    print("  python check_all_direct_generations.py")
    print()
    print("画像を開く:")
    print("  python open_generated_images.py")
