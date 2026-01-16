#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI再起動後、自動で画像生成を実行"""

import requests
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
GALLERY_API = "http://localhost:5559/api/generate"

print("=" * 60)
print("ComfyUI再起動確認と自動画像生成")
print("=" * 60)
print()

# ComfyUIの接続確認（最大30秒待機）
print("ComfyUIの接続を確認中...")
connected = False
for i in range(15):
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        if response.status_code == 200:
            print("[OK] ComfyUI接続成功！")
            connected = True
            break
    except:
        if i == 0:
            print("ComfyUI接続待機中...")
        time.sleep(2)

if not connected:
    print("[ERROR] ComfyUIに接続できませんでした。")
    print("ComfyUIが起動していることを確認してください。")
    print("起動コマンド: powershell -ExecutionPolicy Bypass -File start_comfyui_fixed.ps1")
    sys.exit(1)

print()
print("-" * 60)
print()

# 画像生成を実行
print("ムフフモード：日本人の清楚系ギャル10枚生成を開始...")
print()

job_ids = []

for i in range(10):
    import random
    import hashlib
    import uuid
    
    # モデルをランダムに選択
    models = [
        "realisian_v60.safetensors",
        "realisticVisionV60B1_v51HyperVAE.safetensors",
        "speciosa25D_v12.safetensors",
        "speciosaRealistica_v12b.safetensors",
        "uwazumimixILL_v50.safetensors",
        "shibari_v20.safetensors"
    ]
    model = random.choice(models)
    
    # プロンプト要素
    expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes"]
    faces = ["beautiful face", "perfect face", "refined face", "cute face"]
    bodies = ["toned body", "fit body", "athletic body", "slim body"]
    poses = ["cowgirl position", "missionary position", "doggy style", "69 position"]
    scenes = ["during sex", "sexual act", "intimate moment", "making love"]
    
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        f"naked, {random.choice(poses)}",
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        "high quality", "masterpiece", "best quality", "perfect anatomy"
    ]
    prompt = ", ".join(prompt_parts)
    
    # パラメータをランダムに設定
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        steps = random.choice([45, 50, 55, 60])
        width, height = random.choice([(768, 1024), (1024, 768), (832, 1216)])
    
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral"])
    scheduler = random.choice(["normal", "karras", "exponential"])
    
    # Seed生成
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    seed = (time_seed ^ random_seed ^ model_hash ^ prompt_hash) % (2**32)
    
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
    print(f"  解像度: {width}x{height}, ステップ: {steps}, CFG: {guidance_scale}")
    
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
                job_ids.append((job_id, model))
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [HTTP ERROR] {response.status_code}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    if i < 9:
        time.sleep(2)

print()
print("=" * 60)
print(f"[完了] {len(job_ids)}件の画像生成ジョブを送信しました")
print("=" * 60)
print()
print("ジョブID一覧:")
for i, (job_id, model) in enumerate(job_ids, 1):
    print(f"  {i}. {job_id} ({model})")
print()
print("画像生成の進行状況は以下で確認できます:")
print("  http://localhost:5559/api/images")
