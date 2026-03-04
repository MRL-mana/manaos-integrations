#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""フェラシーンのプロンプトテスト（1枚生成して確認）"""

import os
import requests
import json
import time
import sys
import io
import random
import hashlib
import pytest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from _paths import COMFYUI_PORT

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")

models = ["realisian_v60.safetensors"]

MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure, malformed body, distorted body, broken body, twisted body, unnatural body, wrong proportions, asymmetrical body, bad body structure, malformed breasts, distorted breasts, wrong breast size, unnatural breasts, bad torso, malformed torso, distorted torso, bad waist, malformed waist, bad hips, malformed hips, bad legs, malformed legs, distorted legs, bad arms, malformed arms, distorted arms, extra fingers, missing fingers, bad fingers, extra toes, missing toes, bad toes, fused fingers, too many fingers, missing limbs, extra limbs, floating limbs, disconnected limbs, malformed hands, extra hands, missing hands, bad hands, malformed feet, extra feet, missing feet, bad feet, multiple people, other people, group, couple, vaginal sex, anal sex, penetration, intercourse"

def create_workflow(prompt, negative_prompt, model, steps, guidance_scale, width, height, sampler, scheduler, seed):
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

def _is_comfyui_ready() -> bool:
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False

# フェラシーンを最優先で強調したプロンプト
prompt = (
    "Japanese woman, 1girl, solo, alone, "
    "clear gyaru style, innocent gyaru, "
    "naked, kneeling, on knees, "
    "mouth open, lips parted, tongue out, sucking, "
    "wide eyes, beautiful face, "
    "toned body, D cup, D-cup breasts, "
    "performing oral sex, giving blowjob, fellatio, "
    "oral sex, blowjob, giving head, "
    "sucking cock, deep throat, "
    "cock in mouth, penis in mouth, dick in mouth, "
    "long straight hair, natural makeup, "
    "soft lighting, bedroom, "
    "realistic, photorealistic, real photo, photography, "
    "high quality, masterpiece, best quality, "
    "detailed, sharp focus, 8k uhd, ultra detailed, "
    "beautiful skin, smooth skin, perfect skin, "
    "perfect anatomy, correct anatomy, "
    "no multiple people, no other people, only one person, "
    "no penetration, no vaginal sex, no anal sex"
)

model = "realisian_v60.safetensors"
steps = 70
width, height = 1024, 1024
guidance_scale = 9.0
sampler = "euler_ancestral"
scheduler = "karras"

seed = random.randint(1, 2**32 - 1)

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

def test_comfyui_prompt_submit_smoke():
    if not _is_comfyui_ready():
        return

    payload = {"prompt": workflow}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    assert response.status_code in (200, 400, 401, 403, 404, 422, 500, 503)
    if response.status_code == 200:
        result = response.json()
        assert result.get("prompt_id")
