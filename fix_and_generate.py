#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI-Managerを無効化してComfyUIを再起動し、画像生成を実行"""

import os
import sys
import io
import time
import requests
import subprocess
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
GALLERY_API = os.getenv("GALLERY_API", "http://localhost:5559/api/generate")
# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
MANAGER_PATH = COMFYUI_PATH / "custom_nodes" / "ComfyUI-Manager"
MANAGER_DISABLED = COMFYUI_PATH / "custom_nodes" / "ComfyUI-Manager.disabled"

print("=" * 60)
print("ComfyUI修正と画像生成")
print("=" * 60)
print()

# 1. ComfyUI-Managerの状態確認と無効化
print("1. ComfyUI-Managerの状態確認:")
if MANAGER_PATH.exists():
    print("   [INFO] ComfyUI-Managerが有効です")
    print("   [実行] ComfyUI-Managerを無効化中...")
    try:
        MANAGER_PATH.rename(MANAGER_DISABLED)
        print("   [OK] ComfyUI-Managerを無効化しました")
    except Exception as e:
        print(f"   [ERROR] 無効化に失敗: {e}")
elif MANAGER_DISABLED.exists():
    print("   [OK] ComfyUI-Managerは既に無効化されています")
else:
    print("   [INFO] ComfyUI-Managerが見つかりません（問題ありません）")

print()

# 2. ComfyUIの状態確認
print("2. ComfyUIの状態確認:")
try:
    response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
    if response.status_code == 200:
        print("   [OK] ComfyUIは起動しています")
        print("   [重要] ComfyUIを再起動してください:")
        print("     新しいコマンドプロンプトで以下を実行:")
        comfyui_path_str = str(COMFYUI_PATH).replace('/', '\\')
        print(f"     cd {comfyui_path_str}")
        print("     set PYTHONIOENCODING=utf-8")
        print("     set PYTHONLEGACYWINDOWSSTDIO=1")
        print("     python main.py")
        print()
        print("     または、バッチファイルを使用:")
        integrations_dir = os.getenv("MANAOS_INTEGRATIONS_DIR", r"C:\Users\mana4\Desktop\manaos_integrations")
        print(f"     cd {integrations_dir}")
        print("     .\\start_comfyui_simple.bat")
    else:
        print(f"   [WARN] ComfyUI接続エラー: {response.status_code}")
except:
    print("   [WARN] ComfyUIに接続できません")
    print("   [重要] ComfyUIを起動してください:")

print()

# 3. 再起動待機と確認
print("3. ComfyUI再起動待機中...")
print("   再起動後、Enterキーを押してください（または30秒後に自動で続行）")
print()

# 30秒待機（またはユーザー入力）
try:
    import select
    import sys
    if sys.stdin.isatty():
        import msvcrt
        start_time = time.time()
        while time.time() - start_time < 30:
            if msvcrt.kbhit():
                msvcrt.getch()
                break
            time.sleep(0.1)
    else:
        time.sleep(10)
except:
    time.sleep(10)

# ComfyUI接続確認
print("   ComfyUI接続を確認中...")
for i in range(6):
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        if response.status_code == 200:
            stats = response.json()
            system = stats.get("system", {})
            print(f"   [OK] ComfyUI接続成功")
            print(f"   ComfyUIバージョン: {system.get('comfyui_version', 'N/A')}")
            break
    except:
        if i < 5:
            print(f"   接続試行 {i+1}/6...")
            time.sleep(5)
        else:
            print("   [WARN] ComfyUIに接続できません。手動で起動してください。")
            sys.exit(1)

print()

# 4. エラー状況確認
print("4. 最新のエラー状況確認:")
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
                print(f"   [WARN] エンコーディングエラー: {encoding_errors}件")
                print("   まだエラーが発生している可能性があります。")
            else:
                print("   [OK] 最近のエラーは見つかりませんでした")
except:
    pass

print()

# 5. 画像生成を実行
print("5. 画像生成を実行中...")
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
    expressions = ["wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes", "large eyes"]
    faces = ["beautiful face", "perfect face", "refined face", "cute face", "neat face", "well-defined face"]
    bodies = ["toned body", "fit body", "athletic body", "slim body", "tight body", "well-toned body"]
    poses = ["cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl", "sitting position"]
    scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment"]
    hair_styles = ["long hair", "short hair", "wavy hair", "straight hair", "curly hair"]
    lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting"]
    
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        f"naked, {random.choice(poses)}",
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),
        random.choice(scenes),
        random.choice(hair_styles),
        random.choice(lighting),
        "high quality", "masterpiece", "best quality", "perfect anatomy", "correct anatomy",
        "detailed", "sharp focus", "8k uhd"
    ]
    prompt = ", ".join(prompt_parts)
    
    # パラメータ
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        steps = random.choice([45, 50, 55, 60])
        width, height = random.choice([(768, 1024), (1024, 768), (832, 1216), (768, 1152)])
    
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras", "exponential"])
    
    # Seed生成（より多様性を持たせる）
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
                job_ids.append((job_id, model, prompt))
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
    for i, (job_id, model, prompt) in enumerate(job_ids, 1):
        print(f"  {i}. {job_id}")
        print(f"     モデル: {model}")
        print(f"     プロンプト: {prompt[:60]}...")
    print()
    print("画像生成の進行状況は以下で確認できます:")
    print("  http://localhost:5559/api/images")
    print()
    print("生成状況を確認するには:")
    print("  python check_generation_status.py")
    print("  python final_status_check.py")
