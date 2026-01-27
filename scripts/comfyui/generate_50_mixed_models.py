#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""いろんなモデルとLoRAを組み合わせて50枚生成"""

import requests
import json
import time
import sys
import io
import random
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"

# モデルとLoRAの検出（既存スクリプトと同じロジック）
COMFYUI_MODELS_DIR = Path("C:/ComfyUI/models/checkpoints")
COMFYUI_LORA_DIR = Path("C:/ComfyUI/models/loras")

available_models = []
available_loras = []

# モデル検出
for model_file in COMFYUI_MODELS_DIR.glob("*.safetensors"):
    available_models.append(model_file.name)
for model_file in COMFYUI_MODELS_DIR.glob("*.ckpt"):
    available_models.append(model_file.name)

# LoRA検出（画像生成用のみ）
if COMFYUI_LORA_DIR.exists():
    for lora_file in COMFYUI_LORA_DIR.glob("*.safetensors"):
        lora_name = lora_file.name
        if not any(kw in lora_name.lower() for kw in ["qwen", "llm", "text"]):
            available_loras.append(lora_name)

# 問題のあるモデルを除外
problematic_models = [
    "0482 dildo masturbation_v1_pony.safetensors",
    "0687 public indecency_v1_pony.safetensors",
    "ltx-2-19b-distilled.safetensors",
    "qqq-BDSM-v3-000010.safetensors",
    "ZIT_Amateur_Nudes_V2.safetensors",
    "wan2.2_t2v_highnoise_masturbation_v1.0.safetensors",
    "waiIllustriousSDXL_v160.safetensors",
]
available_models = [m for m in available_models if m not in problematic_models and "\\" not in m and "/" not in m]


def is_sdxl_model(model_name):
    return any(kw in model_name.lower() for kw in ["sdxl", "xl", "speciosa25d", "uwazumimix", "pony", "illustrious"])


def is_sd3_model(model_name):
    return any(kw in model_name.lower() for kw in ["sd3", "flux"])


def create_workflow_with_multiple_loras(
    prompt,
    negative_prompt,
    model,
    loras=None,
    steps=70,
    guidance_scale=8.5,
    width=1024,
    height=1024,
    sampler="euler_ancestral",
    scheduler="karras",
    seed=1,
):
    """複数LoRA対応のワークフロー作成"""
    workflow = {
        "1": {"inputs": {"ckpt_name": model}, "class_type": "CheckpointLoaderSimple"},
    }

    # 複数LoRAを順次適用
    current_model = ["1", 0]
    current_clip = ["1", 1]
    node_id = 8

    if loras:
        for lora_name, lora_strength in loras:
            workflow[str(node_id)] = {
                "inputs": {
                    "lora_name": lora_name,
                    "strength_model": lora_strength,
                    "strength_clip": lora_strength,
                    "model": current_model,
                    "clip": current_clip,
                },
                "class_type": "LoraLoader",
            }
            current_model = [str(node_id), 0]
            current_clip = [str(node_id), 1]
            node_id += 1

    # テキストエンコーダー
    workflow["2"] = {"inputs": {"text": prompt, "clip": current_clip}, "class_type": "CLIPTextEncode"}
    workflow["3"] = {"inputs": {"text": negative_prompt, "clip": current_clip}, "class_type": "CLIPTextEncode"}

    # サンプラー
    workflow["4"] = {
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": guidance_scale,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": current_model,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["5", 0],
        },
        "class_type": "KSampler",
    }

    workflow["5"] = {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyLatentImage"}
    workflow["6"] = {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"}
    workflow["7"] = {"inputs": {"filename_prefix": "ComfyUI", "images": ["6", 0]}, "class_type": "SaveImage"}
    return workflow


MUFUFU_NEGATIVE_PROMPT = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, multiple people, multiple persons, fellatio, oral sex, blowjob"

print("=" * 60)
print("いろんなモデルとLoRAを組み合わせて50枚生成")
print("=" * 60)
print()
print(f"利用可能なモデル: {len(available_models)}件")
print(f"利用可能なLoRA: {len(available_loras)}件")
print()

# プロンプト要素
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style"]
poses = ["lying", "sitting", "standing", "kneeling", "bent over"]
expressions = ["smile", "happy", "seductive", "innocent", "playful"]
bodies = ["slim body", "toned body", "athletic body", "fit body"]
breast_size = ["medium breasts", "large breasts", "D cup"]
scenes = ["bedroom", "bed", "hotel room", "intimate setting"]
sex_acts = ["sex", "intercourse", "lovemaking", "intimate moment"]
hair_styles = ["long hair", "medium hair", "wavy hair", "straight hair"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting"]

prompt_ids = []

for i in range(50):
    # ランダムにモデルを選択
    model = random.choice(available_models)

    # 複数LoRAをランダムに組み合わせ（0-3個、各50-80%の確率で使用）
    num_loras = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
    loras = []
    if available_loras and num_loras > 0:
        selected_loras = random.sample(available_loras, min(num_loras, len(available_loras)))
        for lora_name in selected_loras:
            lora_strength = round(random.uniform(0.5, 0.8), 2)
            loras.append((lora_name, lora_strength))

    # プロンプト生成
    prompt_parts = [
        "Japanese",
        "Japanese woman",
        "1girl",
        "solo",
        random.choice(clothing_style),
        "naked",
        random.choice(poses),
        random.choice(expressions),
        random.choice(bodies),
        random.choice(breast_size),
        "perfect proportions",
        "correct anatomy",
        "beautiful",
        "gorgeous",
        "stunning",
        random.choice(scenes),
        random.choice(sex_acts),
        random.choice(hair_styles),
        random.choice(lighting),
        "realistic",
        "photorealistic",
        "high quality",
        "masterpiece",
        "detailed",
        "sharp focus",
        "8k uhd",
    ]
    prompt = ", ".join(prompt_parts)

    # パラメータ設定
    if is_sdxl_model(model) or is_sd3_model(model):
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        steps = random.choice([60, 65, 70, 75])
        width, height = random.choice([(768, 1024), (1024, 768), (896, 1152), (1024, 1024)])

    guidance_scale = round(random.uniform(8.0, 9.5), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras", "exponential"])

    seed = random.randint(1, 2**32 - 1)

    workflow = create_workflow_with_multiple_loras(
        prompt=prompt,
        negative_prompt=MUFUFU_NEGATIVE_PROMPT,
        model=model,
        loras=loras if loras else None,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed,
    )

    lora_info = ""
    if loras:
        lora_names = [l[0][:20] for l in loras]
        lora_info = f" + LoRA:{'+'.join(lora_names)}"

    print(f"[{i+1:2d}/50] {model[:35]}{lora_info}")
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
                print("  [ERROR] プロンプトIDが取得できませんでした")
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print()
    time.sleep(1)  # レート制限対策

print("=" * 60)
print(f"生成リクエスト完了: {len(prompt_ids)}件")
print("=" * 60)
print("画像はComfyUIの出力フォルダに保存されます。")
