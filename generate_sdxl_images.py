#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDXLモデルで画像を生成（プロンプトと設定を毎回変える）"""

import requests
import time
import sys
import io
import random

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/generate"

# SDXL候補モデル（6GB以上のモデル）
sdxl_models = [
    "speciosa25D_v12.safetensors",  # 6.62 GB
    "uwazumimixILL_v50.safetensors"  # 6.46 GB
]

# プロンプト要素のバリエーション
poses = [
    "sitting", "lying down", "standing", "kneeling", "bent over",
    "on all fours", "spread legs", "arms up", "back arch", "side view"
]
expressions = [
    "smile", "innocent look", "seductive expression", "pleasure face",
    "blushing", "winking", "open mouth", "tongue out", "closed eyes", "looking at viewer"
]
styles = [
    "clear and pure gyaru style", "cute gyaru", "innocent gyaru",
    "sexy gyaru", "kawaii gyaru", "pure gyaru", "clear gyaru style"
]
scenes = [
    "sexual act", "intimate moment", "erotic scene", "passionate moment",
    "intimate scene", "erotic act", "passionate act", "intimate act"
]
qualities = [
    "high quality", "detailed", "masterpiece", "best quality",
    "ultra detailed", "8k", "photorealistic", "cinematic lighting"
]

# サンプラーとスケジューラーのバリエーション
samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral"]
schedulers = ["karras", "normal", "exponential", "sgm_uniform"]

print("=" * 60)
print("SDXLモデルで画像を生成します（プロンプトと設定を毎回変える）")
print("要素: 日本人、清楚系ギャル、裸、可愛い系ギャル、性行為")
print("=" * 60)
print()

def generate_varied_prompt():
    """バリエーション豊かなプロンプトを生成"""
    style = random.choice(styles)
    pose = random.choice(poses)
    expression = random.choice(expressions)
    scene = random.choice(scenes)
    quality = random.choice(qualities)

    prompt_parts = [
        style,
        f"naked, {pose}",
        expression,
        scene,
        "beautiful body",
        quality
    ]

    return ", ".join(prompt_parts)

job_ids = []

for i in range(10):
    model = sdxl_models[i % len(sdxl_models)]
    prompt = generate_varied_prompt()

    # 毎回異なるパラメータを設定
    seed = random.randint(1, 2**32 - 1)
    steps = random.choice([35, 40, 45, 50])
    guidance_scale = round(random.uniform(7.0, 8.5), 1)
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)

    # 解像度も少し変える（SDXLは1024x1024が標準だが、縦横比を変える）
    aspect_ratios = [
        (1024, 1024),  # 正方形
        (1024, 1280),  # 縦長
        (1280, 1024),  # 横長
        (1152, 1152),  # 少し小さい正方形
    ]
    width, height = random.choice(aspect_ratios)

    print(f"[{i+1}/10] SDXLモデル: {model}")
    print(f"  プロンプト: {prompt}")
    print(f"  解像度: {width}x{height}")
    print(f"  ステップ: {steps}, CFG: {guidance_scale}, サンプラー: {sampler}, スケジューラー: {scheduler}, seed: {seed}")

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
        "mufufu_mode": True  # ムフフモードを有効化
    }

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
                job_ids.append(job_id)
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [HTTP ERROR] {response.status_code}")
            print(f"    レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")

    # リクエスト間隔を空ける
    if i < 9:
        time.sleep(2)

print()
print("=" * 60)
print(f"[完了] {len(job_ids)}件のSDXL画像生成ジョブを送信しました")
print("=" * 60)
print()
print("ジョブID一覧:")
for i, job_id in enumerate(job_ids, 1):
    print(f"  {i}. {job_id}")
print()
print("画像生成の進行状況は以下で確認できます:")
print("  http://localhost:5559/api/job/<job_id>")
print()
print("生成された画像は以下で確認できます:")
print("  http://localhost:5559/api/images")
