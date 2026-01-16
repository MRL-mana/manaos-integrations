#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リアル系で日本人清楚系ギャル10枚生成"""

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

# リアル系モデルのみ使用
models = [
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "realisian_v60.safetensors"
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
print("リアル系で日本人清楚系ギャル10枚生成")
print("=" * 60)
print()

# 清楚系ギャルの要素
expressions = ["innocent eyes", "clear eyes", "bright eyes", "sparkling eyes", "pure eyes", "gentle eyes"]
faces = ["beautiful face", "cute face", "innocent face", "pure face", "refined face", "neat face", "well-defined face"]
bodies = ["slim body", "slender body", "fit body", "toned body", "well-proportioned body"]
poses = ["standing", "sitting", "lying down", "cowgirl position", "missionary position", "doggy style"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment"]
hair_styles = ["long straight hair", "long wavy hair", "bob cut", "shoulder length hair", "ponytail"]
makeup = ["natural makeup", "light makeup", "minimal makeup", "fresh makeup"]
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style"]

prompt_ids = []

for i in range(10):
    model = random.choice(models)
    
    # リアル系で清楚系ギャルのプロンプト
    prompt_parts = [
        "Japanese", "Japanese woman", "1girl",
        random.choice(clothing_style),
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        random.choice(hair_styles),
        random.choice(makeup),
        "realistic", "photorealistic", "real photo", "photography",
        "high quality", "masterpiece", "best quality", "perfect anatomy", "correct anatomy",
        "detailed", "sharp focus", "8k uhd", "ultra detailed", "professional photography"
    ]
    prompt = ", ".join(prompt_parts)
    
    # リアル系モデル用のパラメータ
    steps = random.choice([50, 55, 60])
    width, height = random.choice([(768, 1024), (1024, 768), (832, 1216), (896, 1152)])
    
    guidance_scale = round(random.uniform(7.0, 8.5), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras"])
    
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
    
    print(f"[{i+1:2d}/10] {model}")
    print(f"  {prompt[:75]}...")
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
    
    if i < 9:
        time.sleep(0.5)

print()
print("=" * 60)
print(f"送信完了: {len(prompt_ids)}件")
print("=" * 60)

if len(prompt_ids) > 0:
    print()
    print("プロンプトID一覧:")
    for i, prompt_id in enumerate(prompt_ids, 1):
        print(f"  {i:2d}. {prompt_id}")
    
    print()
    print("画像生成の進行状況を確認中...")
    time.sleep(60)
    
    success_count = 0
    success_files = []
    
    for prompt_id in prompt_ids:
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
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                for img in images:
                                    filename = img.get('filename', 'N/A')
                                    success_files.append(filename)
        except:
            pass
    
    print(f"生成状況: 成功 {success_count}件 / {len(prompt_ids)}件")
    
    if success_files:
        print()
        print(f"生成された画像ファイル ({len(success_files)}件):")
        for filename in success_files:
            print(f"  - {filename}")
    
    print()
    print("画像を開く:")
    print("  python open_generated_images.py")
