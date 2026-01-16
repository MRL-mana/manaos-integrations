#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""他のモデルでも画像を生成（プロンプトと設定を毎回変える）"""

import requests
import time
import sys
import io
import random

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/generate"

# まだ使っていないモデル
other_models = [
    "realisian_v60.safetensors",  # 2.14 GB
    "realisticVisionV60B1_v51HyperVAE.safetensors",  # SD 1.5ベース
    "speciosaRealistica_v12b.safetensors",  # 1.13 GB
    "shibari_v20.safetensors",  # 0.04 GB
    "qqq-BDSM-v3-000010.safetensors",  # 0.04 GB
    "0482 dildo masturbation_v1_pony.safetensors",  # 0.16 GB
    "0687 public indecency_v1_pony.safetensors"  # 0.16 GB
]

# プロンプト要素のバリエーション
poses = [
    "sitting", "lying down", "standing", "kneeling", "bent over",
    "on all fours", "spread legs", "arms up", "back arch", "side view",
    "cowgirl position", "missionary position", "doggy style", "69 position"
]
expressions = [
    "smile", "innocent look", "seductive expression", "pleasure face",
    "blushing", "winking", "open mouth", "tongue out", "closed eyes",
    "looking at viewer", "ecstatic expression", "moaning"
]
styles = [
    "clear and pure gyaru style", "cute gyaru", "innocent gyaru",
    "sexy gyaru", "kawaii gyaru", "pure gyaru", "clear gyaru style",
    "gyaru style", "gyaru fashion"
]
scenes = [
    "sexual act", "intimate moment", "erotic scene", "passionate moment",
    "intimate scene", "erotic act", "passionate act", "intimate act",
    "making love", "having sex", "foreplay"
]
qualities = [
    "high quality", "detailed", "masterpiece", "best quality",
    "ultra detailed", "8k", "photorealistic", "cinematic lighting"
]

# サンプラーとスケジューラーのバリエーション
samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral"]
schedulers = ["karras", "normal", "exponential", "sgm_uniform"]

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

print("=" * 60)
print("他のモデルで画像を生成します（プロンプトと設定を毎回変える）")
print("要素: 日本人、清楚系ギャル、裸、可愛い系ギャル、性行為")
print("=" * 60)
print()

job_ids = []

for i, model in enumerate(other_models):
    prompt = generate_varied_prompt()

    # 毎回異なるパラメータを設定
    seed = random.randint(1, 2**32 - 1)
    steps = random.choice([30, 35, 40, 45])
    guidance_scale = round(random.uniform(7.0, 8.5), 1)
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)

    # 解像度も変える
    aspect_ratios = [
        (768, 1024),  # 縦長
        (1024, 768),  # 横長
        (832, 1216),  # より縦長
        (1216, 832),  # より横長
        (896, 1152),  # 中程度の縦長
    ]
    width, height = random.choice(aspect_ratios)

    print(f"[{i+1}/{len(other_models)}] モデル: {model}")
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
                job_ids.append((job_id, model))
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [HTTP ERROR] {response.status_code}")
            print(f"    レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")

    # リクエスト間隔を空ける
    if i < len(other_models) - 1:
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
print("  http://localhost:5559/api/job/<job_id>")
print()
print("生成された画像は以下で確認できます:")
print("  http://localhost:5559/api/images")
