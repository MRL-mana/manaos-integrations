#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナ好みのリアル系清楚系ギャル20枚生成（フェラなし・モデル追加・LoRA対応）"""

import requests
import json
import time
import sys
import io
import random
import hashlib
from pathlib import Path
import os

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"

# 利用可能なモデル（複数モデル対応）
COMFYUI_MODELS_DIR = Path(os.getenv("COMFYUI_MODELS_DIR", "C:/ComfyUI/models/checkpoints"))
MANA_MODELS_DIR = Path(os.getenv("MANA_MODELS_DIR", "C:/mana_workspace/models"))

# 利用可能なモデル（確実に動作するモデルのみ使用）
# 現在はrealisian_v60.safetensorsのみ使用（他のモデルでエラーが発生しているため）
available_models = [
    "realisian_v60.safetensors"  # 確実に動作するモデル
]

# 利用可能なLoRAを自動検出
COMFYUI_LORA_DIR = Path("C:/ComfyUI/models/loras")
available_loras = []
if COMFYUI_LORA_DIR.exists():
    for lora_file in COMFYUI_LORA_DIR.glob("*.safetensors"):
        available_loras.append(lora_file.name)
    for lora_file in COMFYUI_LORA_DIR.glob("*.ckpt"):
        available_loras.append(lora_file.name)

# LoRAを使用するか（オプション、空の場合は使用しない）
use_lora = random.choice([True, False]) if available_loras else False
selected_lora = random.choice(available_loras) if use_lora and available_loras else None

MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure, malformed body, distorted body, broken body, twisted body, unnatural body, wrong proportions, asymmetrical body, bad body structure, malformed breasts, distorted breasts, wrong breast size, unnatural breasts, bad torso, malformed torso, distorted torso, bad waist, malformed waist, bad hips, malformed hips, bad legs, malformed legs, distorted legs, bad arms, malformed arms, distorted arms, extra fingers, missing fingers, bad fingers, extra toes, missing toes, bad toes, fused fingers, too many fingers, missing limbs, extra limbs, floating limbs, disconnected limbs, malformed hands, extra hands, missing hands, bad hands, malformed feet, extra feet, missing feet, bad feet, multiple people, other people, group, couple, oral sex, fellatio, blowjob, giving head, sucking cock, deep throat, performing oral, mouth sex, cock in mouth, penis in mouth"

def create_workflow(prompt, negative_prompt, model, lora_name=None, lora_strength=0.8, steps=70, guidance_scale=8.5, width=1024, height=1024, sampler="euler_ancestral", scheduler="karras", seed=1):
    """ComfyUIワークフローを作成（LoRA対応）"""
    workflow = {
        "1": {
            "inputs": {"ckpt_name": model},
            "class_type": "CheckpointLoaderSimple"
        }
    }
    
    # LoRAを追加（オプション）
    if lora_name:
        workflow["8"] = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["1", 0],
                "clip": ["1", 1]
            },
            "class_type": "LoraLoader"
        }
        model_output = ["8", 0]
        clip_output = ["8", 1]
    else:
        model_output = ["1", 0]
        clip_output = ["1", 1]
    
    workflow["2"] = {
        "inputs": {"text": prompt, "clip": clip_output},
        "class_type": "CLIPTextEncode"
    }
    workflow["3"] = {
        "inputs": {"text": negative_prompt, "clip": clip_output},
        "class_type": "CLIPTextEncode"
    }
    workflow["4"] = {
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": guidance_scale,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": model_output,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    }
    workflow["5"] = {
        "inputs": {"width": width, "height": height, "batch_size": 1},
        "class_type": "EmptyLatentImage"
    }
    workflow["6"] = {
        "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
        "class_type": "VAEDecode"
    }
    workflow["7"] = {
        "inputs": {"filename_prefix": "ComfyUI", "images": ["6", 0]},
        "class_type": "SaveImage"
    }
    return workflow

print("=" * 60)
print("マナ好みのリアル系清楚系ギャル30枚生成")
print("（女性一人・美しさ・魅力・引き締まった体・Dカップ・性行為・フェラなし）")
print("=" * 60)
print()

print(f"利用可能なモデル数: {len(available_models)}")
if available_models:
    print("モデル一覧:")
    for model in available_models[:5]:
        print(f"  - {model}")
    if len(available_models) > 5:
        print(f"  ... 他 {len(available_models) - 5} 件")

print()
print(f"利用可能なLoRA数: {len(available_loras)}")
if available_loras:
    print("LoRA一覧:")
    for lora in available_loras[:5]:
        print(f"  - {lora}")
    if len(available_loras) > 5:
        print(f"  ... 他 {len(available_loras) - 5} 件")
print()

# マナ好みの清楚系ギャルの要素（美しさと魅力を強調・この子がタイプのスタイル）
expressions = ["innocent eyes", "clear eyes", "bright eyes", "sparkling eyes", "pure eyes", "gentle eyes", "wide eyes", "big eyes", "beautiful eyes", "captivating eyes", "charming eyes", "large eyes", "round eyes", "doll-like eyes", "coy expression", "shy expression"]
faces = ["beautiful face", "cute face", "innocent face", "pure face", "refined face", "neat face", "well-defined face", "pretty face", "attractive face", "gorgeous face", "stunning face", "perfect face", "flawless face", "elegant face", "round face", "doll-like face", "fair skin", "smooth skin", "slight blush"]
# 引き締まった体とDカップを強調（マナ好み）
bodies = ["toned body", "fit body", "athletic body", "slim toned body", "well-toned body", "muscular toned body", "defined body", "perfect body", "ideal body", "beautiful body", "sexy body", "alluring body"]
breast_size = ["D cup", "D-cup breasts", "medium breasts", "proportional breasts", "perfect breasts", "beautiful breasts", "natural breasts"]
# 性行為シーン（フェラなし）
poses = ["standing", "sitting", "lying down", "cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl", "spread legs", "legs spread"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment", "romantic scene", "erotic scene"]
sex_acts = ["sexual intercourse", "sex act", "having sex", "during sex", "making love", "penetration", "sexual activity"]
hair_styles = ["long straight hair", "long wavy hair", "bob cut", "shoulder length hair", "ponytail", "twintails", "curly hair", "short hair", "hair bun", "hair partially tied up", "loose strands", "straight bangs"]
makeup = ["natural makeup", "light makeup", "minimal makeup", "fresh makeup", "soft makeup", "cute makeup", "subtle makeup", "defined eyelashes"]
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style", "sweet gyaru style", "gyaru fashion"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting", "studio lighting", "romantic lighting", "bright lighting", "sunny day", "daylight"]
backgrounds = ["bedroom", "bed", "hotel room", "intimate setting", "private room", "romantic atmosphere", "luxury room", "urban setting", "outdoor", "public space", "street", "city"]

prompt_ids = []

for i in range(30):
    model = random.choice(available_models)
    
    # LoRAは一旦無効化（Qwen系LoRAは画像生成用ではないため）
    # 将来的に画像生成用LoRAが追加されたら有効化
    lora_name = None
    lora_strength = None
    
    # マナ好みのリアル系清楚系ギャルプロンプト（女性一人・美しさ・魅力・身体崩れ防止・引き締まった体・Dカップ・性行為・フェラなし・この子がタイプのスタイル）
    prompt_parts = [
        "Japanese", "Japanese woman", "1girl", "solo", "alone", "single woman",  # 女性一人を強調
        random.choice(clothing_style),
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),  # 引き締まった体（マナ好み）
        random.choice(breast_size),  # Dカップ
        "perfect proportions", "well-proportioned body", "natural proportions", "ideal proportions",
        "correct anatomy", "perfect anatomy", "accurate anatomy", "flawless anatomy",
        "natural body structure", "proper body structure", "beautiful body structure",
        "beautiful", "gorgeous", "stunning", "attractive", "sexy", "alluring", "captivating", "charming",
        random.choice(scenes),  # 性行為シーン
        random.choice(sex_acts),  # 性行為
        random.choice(hair_styles),
        random.choice(makeup),
        random.choice(lighting),
        random.choice(backgrounds),
        "realistic", "photorealistic", "real photo", "photography",
        "high quality", "masterpiece", "best quality", "ultra quality", "perfect quality",
        "detailed", "sharp focus", "8k uhd", "ultra detailed", "professional photography",
        "beautiful skin", "smooth skin", "flawless skin", "perfect skin",
        "no body distortion", "no deformation", "no malformation",
        "aesthetic", "artistic", "elegant", "refined",
        "no multiple people", "no other people", "only one person",  # 一人であることを強調
        "doll-like", "anime-inspired", "gyaru aesthetic"  # この子がタイプのスタイル要素
    ]
    prompt = ", ".join(prompt_parts)
    
    # マナ好みの高品質パラメータ（身体崩れ防止・美しさ重視）
    steps = random.choice([60, 65, 70, 75])
    width, height = random.choice([
        (768, 1024), (1024, 768), (832, 1216), (896, 1152), 
        (960, 1280), (1024, 1024), (896, 1280)
    ])
    
    guidance_scale = round(random.uniform(8.0, 9.5), 1)
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
        lora_name=lora_name,
        lora_strength=lora_strength,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed
    )
    
    lora_info = f" + LoRA:{lora_name[:30]}" if lora_name else ""
    print(f"[{i+1:2d}/30] {model[:40]}{lora_info}")
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
    
    if i < 29:
        time.sleep(0.3)

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
    print("（生成には時間がかかります）")
    print()
    print("生成状況の確認:")
    print("  python check_20_mana_no_fellatio.py")
