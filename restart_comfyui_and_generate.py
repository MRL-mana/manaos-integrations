#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUIを再起動して画像生成を実行"""

import requests
import time
import sys
import io
import subprocess
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from _paths import COMFYUI_PORT, GALLERY_PORT

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/generate"

print("=" * 60)
print("ComfyUI再起動と画像生成")
print("=" * 60)
print()

# 1. ComfyUIの状態確認
print("1. ComfyUIの状態確認:")
try:
    response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
    if response.status_code == 200:
        print("   [OK] ComfyUIは起動しています")
    else:
        print(f"   [WARN] ComfyUI接続エラー: {response.status_code}")
except Exception:
    print("   [WARN] ComfyUIに接続できません")

print()

# 2. 最新のエラー確認
print("2. 最新のエラー確認:")
try:
    response = requests.get(f"{COMFYUI_URL}/history", timeout=5)
    if response.status_code == 200:
        history = response.json()
        if history:
            items = list(history.items())[-3:]
            encoding_errors = 0
            for prompt_id, data in items:
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                if status_str == "error":
                    messages = status.get("messages", [])
                    for msg in messages:
                        if msg[0] == "execution_error":
                            error_data = msg[1]
                            error_msg = error_data.get('exception_message', 'N/A')
                            if "Invalid argument" in error_msg or "Errno 22" in error_msg:
                                encoding_errors += 1
                            break
            
            if encoding_errors > 0:
                print(f"   エンコーディングエラー: {encoding_errors}件")
                print("   [重要] ComfyUIの再起動が必要です")
                print("   手動で再起動してください:")
                print("     .\\start_comfyui_simple.bat")
                print("   または新しいコマンドプロンプトで:")
                print("     cd C:\\ComfyUI")
                print("     set PYTHONIOENCODING=utf-8")
                print("     set PYTHONLEGACYWINDOWSSTDIO=1")
                print("     python main.py")
except Exception:
    pass

print()

# 3. 画像生成を試行
print("3. 画像生成を試行中...")
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

import random
import hashlib

for i in range(10):
    model = random.choice(models)
    
    # プロンプト要素
    expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes"]
    faces = ["beautiful face", "perfect face", "refined face", "cute face", "neat face"]
    bodies = ["toned body", "fit body", "athletic body", "slim body", "tight body"]
    poses = ["cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl"]
    scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex"]
    
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        f"naked, {random.choice(poses)}",
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        "high quality", "masterpiece", "best quality", "perfect anatomy", "correct anatomy"
    ]
    prompt = ", ".join(prompt_parts)
    
    # パラメータ
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
    print(f"  プロンプト: {prompt[:70]}...")
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

if len(job_ids) > 0:
    print("ジョブID一覧:")
    for i, (job_id, model) in enumerate(job_ids, 1):
        print(f"  {i}. {job_id} ({model})")
    print()
    print("注意: エンコーディングエラーが発生している場合、")
    print("ComfyUIを再起動してください:")
    print("  .\\start_comfyui_simple.bat")
    print()
    print("画像生成の進行状況は以下で確認できます:")
    print("  http://127.0.0.1:5559/api/images")
