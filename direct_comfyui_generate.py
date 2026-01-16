#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUIに直接画像生成を送信"""

import requests
import json
import time
import sys
import io
import random
import hashlib
import uuid

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"

# ムフフモード設定のインポート（身体崩れ対策強化版）
try:
    from mufufu_config import (
        MUFUFU_NEGATIVE_PROMPT,
        ANATOMY_POSITIVE_TAGS,
        OPTIMIZED_PARAMS
    )
    print("✅ ムフフ設定ファイルを読み込みました（身体崩れ対策強化版）")
except ImportError:
    # フォールバック: 旧バージョン（互換性のため）
    MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure"
    ANATOMY_POSITIVE_TAGS = ""
    OPTIMIZED_PARAMS = {}
    print("⚠️ ムフフ設定ファイルが見つかりません。旧バージョンを使用します。")

def create_workflow(prompt, negative_prompt, model, steps, guidance_scale, width, height, sampler, scheduler, seed):
    """ComfyUIワークフローを作成"""
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "4": {
            "inputs": {
                "seed": seed if seed is not None else int(time.time() * 1000) % (2**32),
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
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["6", 0]
            },
            "class_type": "SaveImage"
        }
    }
    return workflow

print("=" * 60)
print("ComfyUI直接画像生成")
print("=" * 60)
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

prompt_ids = []

for i in range(10):
    model = random.choice(models)
    
    # 身体崩れ対策タグを先頭に配置（重要）
    prompt_parts = []
    if ANATOMY_POSITIVE_TAGS:
        prompt_parts.append(ANATOMY_POSITIVE_TAGS)
    
    prompt_parts.extend([
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        "high quality", "masterpiece", "best quality", "perfect anatomy"
    ])
    prompt = ", ".join(prompt_parts)
    
    # 身体崩れ対策: パラメータを最適化
    if OPTIMIZED_PARAMS:
        # 推奨パラメータを使用（身体崩れを減らすため）
        if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
            steps = OPTIMIZED_PARAMS.get("steps", 50)
            width, height = random.choice([(1024, 1024), (1024, 1280)])
        else:
            steps = max(OPTIMIZED_PARAMS.get("steps", 50), random.choice([45, 50, 55]))
            # 解像度が低すぎる場合は最適化
            width, height = random.choice([(1024, 1024), (1024, 1280), (768, 1024)])
            if width < 1024 or height < 1024:
                width, height = (1024, 1024)  # 最低1024x1024を保証
        
        guidance_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
        sampler = OPTIMIZED_PARAMS.get("sampler", "dpmpp_2m")
        scheduler = OPTIMIZED_PARAMS.get("scheduler", "karras")
    else:
        # フォールバック: 旧バージョン
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
    
    print(f"[{i+1}/10] {model}")
    print(f"  {prompt[:60]}...")
    
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
            print(f"  [HTTP {response.status_code}] {response.text[:100]}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    time.sleep(1)

print()
print("=" * 60)
print(f"送信完了: {len(prompt_ids)}件")
print("=" * 60)

if len(prompt_ids) > 0:
    print()
    print("プロンプトID一覧:")
    for i, prompt_id in enumerate(prompt_ids, 1):
        print(f"  {i}. {prompt_id}")
    print()
    print("画像生成の進行状況を確認中...")
    time.sleep(30)
    
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
                    outputs = data.get("outputs", {})
                    has_images = any("images" in node_output for node_output in outputs.values())
                    
                    if status_str == "success" and has_images:
                        success_count += 1
        except:
            pass
    
    print(f"生成状況: 成功 {success_count}件 / {len(prompt_ids)}件")
    print()
    print("詳細確認:")
    print("  python check_all_recent_jobs.py")
