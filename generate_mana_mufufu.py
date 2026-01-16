#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナ好みのムフフ画像生成スクリプト"""

import requests
import time
import sys
import io
import random

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/generate"

# SDXL候補モデル
sdxl_models = [
    "speciosa25D_v12.safetensors",
    "uwazumimixILL_v50.safetensors"
]

# マナ好みのムフフプロンプト構成要素
# 既存のスクリプトの傾向（ギャル、清楚、高品質）をベースにアレンジ
situations = [
    "in a cozy bedroom, sunlight filtering through curtains",
    "at a private hot spring, steam rising",
    "relaxing on a plush sofa, dimly lit room",
    "in a luxurious hotel suite, night city view",
    "changing clothes in a locker room"
]

clothing_states = [
    "wearing oversized white shirt only, unbuttoned",
    "wearing cute lingerie, lace details",
    "wrapped in a bath towel, slipping off",
    "wearing a sheer baby doll nightie",
    "naked, covered by soap bubbles"
]

character_styles = [
    "cute japanese gal, pink beige hair, joyful expression",
    "clear and pure beauty, black hair, shy blushing face",
    "stylish gyaru, blonde hair, confident smile",
    "soft and fluffy atmosphere, brown hair, gentle eyes"
]

actions = [
    "looking back at viewer, seductive gaze",
    "lying on bed, stretching body, curves emphasized",
    "adjusting strap, slightly embarrassed",
    "bending over forward, cleavage visible",
    "sitting w-shape, looking up with moist eyes"
]

# ムフフモード設定のインポート（身体崩れ対策強化版）
try:
    from mufufu_config import (
        MUFUFU_NEGATIVE_PROMPT,
        ANATOMY_POSITIVE_TAGS,
        QUALITY_TAGS,
        OPTIMIZED_PARAMS,
        build_mufufu_prompt
    )
    print("✅ ムフフ設定ファイルを読み込みました（身体崩れ対策強化版）")
    quality_tags = QUALITY_TAGS
except ImportError:
    # フォールバック: 旧バージョン
    MUFUFU_NEGATIVE_PROMPT = ""
    ANATOMY_POSITIVE_TAGS = ""
    OPTIMIZED_PARAMS = {}
    quality_tags = "masterpiece, best quality, ultra detailed, 8k, cinematic lighting, depth of field, soft skin, beautiful anatomy"
    print("⚠️ ムフフ設定ファイルが見つかりません。旧バージョンを使用します。")

def generate_mana_prompt():
    """マナ好みの組み合わせでプロンプト生成（身体崩れ対策強化版）"""
    situation = random.choice(situations)
    clothing = random.choice(clothing_states)
    character = random.choice(character_styles)
    action = random.choice(actions)
    
    # 身体崩れ対策タグを先頭に配置（重要）
    if ANATOMY_POSITIVE_TAGS:
        prompt = f"{ANATOMY_POSITIVE_TAGS}, {quality_tags}, {character}, {clothing}, {action}, {situation}, nsfw, erotic, mufufu"
    else:
        # フォールバック: 旧バージョン
        prompt = f"{quality_tags}, {character}, {clothing}, {action}, {situation}, nsfw, erotic, mufufu"
    return prompt

print("=" * 60)
print("マナ好みのムフフ画像生成を開始します...")
print("=" * 60)

job_ids = []

# 5枚生成
for i in range(5):
    model = random.choice(sdxl_models)
    prompt = generate_mana_prompt()
    
    # パラメータのゆらぎ
    seed = random.randint(1, 2**32 - 1)
    # 縦長で全身・スタイルを強調
    width, height = (1024, 1280) 
    
    print(f"[{i+1}/5] 生成中...")
    print(f"  モデル: {model}")
    print(f"  プロンプト: {prompt[:100]}...")
    
    # 身体崩れ対策: パラメータを最適化
    if OPTIMIZED_PARAMS:
        steps = OPTIMIZED_PARAMS.get("steps", 50)
        guidance_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
        sampler = OPTIMIZED_PARAMS.get("sampler", "dpmpp_2m")
        scheduler = OPTIMIZED_PARAMS.get("scheduler", "karras")
        negative_prompt = MUFUFU_NEGATIVE_PROMPT if MUFUFU_NEGATIVE_PROMPT else "worst quality, low quality, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped, jpeg artifacts, signature, watermark, username, blurry"
    else:
        # フォールバック: 旧バージョン
        steps = 40
        guidance_scale = 7.5
        sampler = "dpmpp_2m"
        scheduler = "karras"
        negative_prompt = "worst quality, low quality, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped, jpeg artifacts, signature, watermark, username, blurry"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
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
    
    try:
        response = requests.post(GALLERY_API, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                job_ids.append(job_id)
                print(f"  ✅ 受付成功: {job_id}")
            else:
                print(f"  ❌ エラー: {result.get('error')}")
        else:
            print(f"  ❌ HTTPエラー: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ 例外発生: {e}")
    
    if i < 4:
        time.sleep(1)

print("\n" + "=" * 60)
print(f"生成リクエスト完了: {len(job_ids)}件")
print("画像は http://localhost:5559/api/images で確認できます")
