#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナ好みのリアル系清楚系ギャル20枚生成"""

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

# 成功しているモデルのみ使用
models = [
    "realisian_v60.safetensors"  # このモデルは確実に動作する
]

MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure, malformed body, distorted body, broken body, twisted body, unnatural body, wrong proportions, asymmetrical body, bad body structure, malformed breasts, distorted breasts, wrong breast size, unnatural breasts, bad torso, malformed torso, distorted torso, bad waist, malformed waist, bad hips, malformed hips, bad legs, malformed legs, distorted legs, bad arms, malformed arms, distorted arms, extra fingers, missing fingers, bad fingers, extra toes, missing toes, bad toes, fused fingers, too many fingers, missing limbs, extra limbs, floating limbs, disconnected limbs, malformed hands, extra hands, missing hands, bad hands, malformed feet, extra feet, missing feet, bad feet, multiple people, other people, group, couple, vaginal sex, anal sex, penetration, intercourse"

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
print("マナ好みのリアル系清楚系ギャル20枚生成")
print("（女性一人・美しさ・魅力・引き締まった体・Dカップ・フェラ）")
print("=" * 60)
print()
print("使用モデル: realisian_v60.safetensors（確実に動作するモデル）")
print()

# マナ好みの清楚系ギャルの要素（美しさと魅力を強調）
expressions = ["innocent eyes", "clear eyes", "bright eyes", "sparkling eyes", "pure eyes", "gentle eyes", "wide eyes", "big eyes", "beautiful eyes", "captivating eyes", "charming eyes"]
faces = ["beautiful face", "cute face", "innocent face", "pure face", "refined face", "neat face", "well-defined face", "pretty face", "attractive face", "gorgeous face", "stunning face", "perfect face", "flawless face", "elegant face"]
# 引き締まった体とDカップを強調（マナ好み）
bodies = ["toned body", "fit body", "athletic body", "slim toned body", "well-toned body", "muscular toned body", "defined body", "perfect body", "ideal body", "beautiful body", "sexy body", "alluring body"]
breast_size = ["D cup", "D-cup breasts", "medium breasts", "proportional breasts", "perfect breasts", "beautiful breasts", "natural breasts"]
# フェラシーン専用のポーズ
poses = ["kneeling", "on knees", "kneeling position", "on all fours", "crawling position", "bent over", "leaning forward"]
# フェラシーン専用のシーン
scenes = ["performing oral sex", "giving blowjob", "fellatio", "oral sex", "sucking cock", "deep throat", "mouth on penis"]
# フェラシーン専用の性行為
sex_acts = ["oral sex", "fellatio", "blowjob", "giving head", "sucking cock", "deep throat", "performing oral", "mouth sex"]
oral_acts = ["oral sex", "fellatio", "blowjob", "giving head", "sucking cock", "deep throat", "performing oral", "mouth on penis", "cock in mouth", "penis in mouth", "sucking dick"]
hair_styles = ["long straight hair", "long wavy hair", "bob cut", "shoulder length hair", "ponytail", "twintails", "curly hair", "short hair"]
makeup = ["natural makeup", "light makeup", "minimal makeup", "fresh makeup", "soft makeup", "cute makeup"]
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style", "sweet gyaru style"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting", "studio lighting", "romantic lighting"]
backgrounds = ["bedroom", "bed", "hotel room", "intimate setting", "private room", "romantic atmosphere", "luxury room"]

prompt_ids = []

for i in range(20):
    model = random.choice(models)
    
    # マナ好みのリアル系清楚系ギャルプロンプト（女性一人・美しさ・魅力・身体崩れ防止・引き締まった体・Dカップ・フェラ）
    # フェラシーンを最優先で配置（プロンプトの前半に配置して重みを上げる）
    prompt_parts = [
        "Japanese", "Japanese woman", "1girl", "solo", "alone", "single woman",  # 女性一人を強調
        random.choice(clothing_style),
        # フェラシーンを最優先で配置
        random.choice(scenes),  # フェラシーン（最優先）
        random.choice(sex_acts),  # フェラ性行為（最優先）
        random.choice(oral_acts),  # フェラを強調（最優先）
        "performing oral sex", "giving blowjob", "fellatio",  # 追加のフェラタグ
        "naked", random.choice(poses),  # フェラ専用ポーズ
        "mouth open", "lips parted", "tongue out", "sucking",  # フェラの口の描写
        "cock in mouth", "penis in mouth", "dick in mouth", "penis in her mouth",  # より明確に（重複して強調）
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),  # 引き締まった体（マナ好み）
        random.choice(breast_size),  # Dカップ
        "perfect proportions", "well-proportioned body", "natural proportions", "ideal proportions",
        "correct anatomy", "perfect anatomy", "accurate anatomy", "flawless anatomy",
        "natural body structure", "proper body structure", "beautiful body structure",
        "beautiful", "gorgeous", "stunning", "attractive", "sexy", "alluring", "captivating", "charming",
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
        "no penetration", "no vaginal sex", "no anal sex"  # フェラ以外の性行為を除外
    ]
    prompt = ", ".join(prompt_parts)
    
    # マナ好みの高品質パラメータ（身体崩れ防止・美しさ重視）
    steps = random.choice([60, 65, 70, 75])  # マナ好みの高品質生成のためステップ数をさらに増加
    width, height = random.choice([
        (768, 1024), (1024, 768), (832, 1216), (896, 1152), 
        (960, 1280), (1024, 1024), (896, 1280)
    ])
    
    guidance_scale = round(random.uniform(8.0, 9.5), 1)  # マナ好みの美しさを実現するためCFGをさらに上げる
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
    
    print(f"[{i+1:2d}/20] {model}")
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
    
    if i < 19:
        time.sleep(0.3)  # 送信間隔を短縮

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
    print("  python check_20_mana_preference.py")
