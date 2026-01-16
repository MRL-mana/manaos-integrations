#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ムフフモード：日本人の清楚系ギャル10枚生成（プロンプトと設定を毎回変える）"""

import requests
import time
import sys
import io
import random
import hashlib
import uuid

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GALLERY_API = "http://localhost:5559/api/generate"

# 利用可能なモデル
models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosa25D_v12.safetensors",
    "speciosaRealistica_v12b.safetensors",
    "uwazumimixILL_v50.safetensors",
    "shibari_v20.safetensors"
]

# プロンプト要素のバリエーション
expressions = [
    "wide eyes", "big eyes", "sparkling eyes", "bright eyes", "clear eyes",
    "innocent eyes", "beautiful eyes", "detailed eyes", "expressive eyes",
    "large eyes", "round eyes", "alert eyes", "open eyes", "clear gaze"
]

face_qualities = [
    "beautiful face", "perfect face", "well-proportioned face", "symmetrical face",
    "refined face", "elegant face", "cute face", "lovely face", "attractive face",
    "delicate features", "fine features", "neat face", "tidy face", "clean face"
]

body_types = [
    "toned body", "fit body", "slim body", "athletic body", "well-defined body",
    "muscular body", "lean body", "defined muscles", "tight body", "firm body",
    "sculpted body", "chiseled body", "well-toned", "trim body", "sleek body"
]

poses = [
    "cowgirl position", "missionary position", "doggy style", "69 position",
    "reverse cowgirl", "standing position", "sitting position", "kneeling position",
    "bent over", "on all fours", "spread legs", "legs up", "one leg up",
    "lying on back", "lying on stomach", "squatting", "leaning forward"
]

scenes = [
    "during sex", "sexual act", "intimate moment", "passionate moment",
    "making love", "having sex", "during intercourse", "in the act",
    "intimate scene", "erotic scene", "passionate act", "intimate act"
]

hair_styles = [
    "long hair", "medium hair", "straight hair", "wavy hair", "soft hair",
    "smooth hair", "silky hair", "shiny hair", "well-groomed hair", "neat hair"
]

lighting = [
    "natural lighting", "soft lighting", "warm lighting", "dramatic lighting",
    "rim lighting", "backlighting", "side lighting", "soft natural light"
]

backgrounds = [
    "bedroom", "bed", "sofa", "hotel room", "dim room", "warm room",
    "cozy room", "intimate setting", "private room"
]

camera_angles = [
    "close-up", "medium shot", "full body", "upper body", "from above",
    "from below", "from side", "from front", "low angle", "eye level"
]

qualities = [
    "high quality", "detailed", "masterpiece", "best quality", "ultra detailed",
    "8k", "photorealistic", "cinematic lighting", "professional photography",
    "sharp focus", "perfect anatomy", "high resolution", "4k"
]

# 身体構造を強化するタグ
anatomy_tags = [
    "perfect anatomy", "correct anatomy", "proper proportions", "well-proportioned body",
    "natural body", "realistic body structure", "anatomically correct",
    "correct body structure", "natural proportions", "realistic proportions"
]

def generate_varied_prompt(index):
    """バリエーション豊かなプロンプトを生成"""
    # 基本要素をランダムに選択
    expression = random.choice(expressions)
    face = random.choice(face_qualities)
    body = random.choice(body_types)
    pose = random.choice(poses)
    scene = random.choice(scenes)
    hair = random.choice(hair_styles)
    lighting_elem = random.choice(lighting)
    background = random.choice(backgrounds)
    angle = random.choice(camera_angles)
    
    # 品質タグを複数選択（3-5個）
    quality_tags = random.sample(qualities, k=random.randint(3, 5))
    
    # 身体構造タグを必ず2-4個含める
    anatomy_tag = random.sample(anatomy_tags, k=random.randint(2, 4))
    
    # 追加の詳細要素（ランダムに追加）
    additional_details = []
    detail_options = [
        "sweat", "wet", "glossy skin", "smooth skin", "soft skin",
        "detailed hands", "detailed feet", "realistic", "photorealistic",
        "natural", "lifelike", "beautiful", "attractive", "charming"
    ]
    if random.random() < 0.6:  # 60%の確率で追加
        num_details = random.randint(1, 3)
        additional_details = random.sample(detail_options, k=num_details)
    
    # プロンプトの組み立て
    prompt_parts = [
        "Japanese", "clear and pure gyaru style", "innocent gyaru",
        f"naked, {pose}",
        expression,
        face,
        body,
        scene,
        hair,
        lighting_elem,
        f"in {background}",
        angle,
        ", ".join(anatomy_tag),
        ", ".join(quality_tags)
    ]
    
    # 追加の詳細要素がある場合は追加
    if additional_details:
        prompt_parts.insert(random.randint(8, len(prompt_parts) - 1), ", ".join(additional_details))
    
    # 順序をランダムにシャッフル（最初の3要素は固定）
    fixed_start = prompt_parts[:3]
    rest_parts = prompt_parts[3:]
    random.shuffle(rest_parts)
    
    return ", ".join(fixed_start + rest_parts)

def generate_negative_prompt():
    """バリエーションのあるネガティブプロンプトを生成"""
    base_negative = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume"
    anatomy_negatives = [
        "bad anatomy", "deformed body", "broken body", "twisted body",
        "distorted body", "incorrect anatomy", "wrong proportions",
        "unnatural body", "broken limbs", "extra limbs",
        "deformed limbs", "broken bones", "twisted spine", "distorted torso"
    ]
    other_negatives = [
        "bad hands", "blurry", "low quality", "worst quality", "normal quality",
        "jpeg artifacts", "watermark", "signature", "username", "text",
        "duplicate", "ugly", "deformed", "poorly drawn", "bad proportions",
        "disfigured", "mutation", "mutated", "mutilated", "bad art",
        "bad structure", "out of frame", "cropped", "missing fingers",
        "extra digit", "fewer digits"
    ]
    
    # 身体構造のネガティブを3-5個含める
    selected_anatomy = random.sample(anatomy_negatives, k=random.randint(3, 5))
    # その他のネガティブ要素を5-10個含める
    additional_others = ", ".join(random.sample(other_negatives, k=random.randint(5, 10)))
    
    return f"{base_negative}, {', '.join(selected_anatomy)}, {additional_others}"

print("=" * 60)
print("ムフフモード：日本人の清楚系ギャル10枚生成")
print("要素: 裸、目がパッチリ、整った顔、引き締まった体、性行為中")
print("=" * 60)
print()

job_ids = []

for i in range(10):
    model = random.choice(models)
    prompt = generate_varied_prompt(i)
    
    # 毎回完全に異なるパラメータを設定
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    uuid_hash = int(hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    index_seed = (i * 7919) % (2**32)  # 素数を使ったインデックスベースのシード
    microsecond_seed = int((time.time() % 1) * 1000000) % (2**32)
    seed = (time_seed ^ random_seed ^ index_seed ^ model_hash ^ prompt_hash ^ uuid_hash ^ microsecond_seed) % (2**32)
    
    # モデルに応じてステップ数と解像度を調整
    if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
        steps = random.choice([50, 55, 60, 65, 70])
        aspect_ratios = [
            (1024, 1024), (1024, 1280), (1280, 1024), (1152, 1152),
            (1024, 1536), (1536, 1024), (1088, 1088), (1216, 1216)
        ]
    else:
        steps = random.choice([45, 50, 55, 60, 65])
        aspect_ratios = [
            (768, 1024), (1024, 768), (832, 1216), (1216, 832),
            (896, 1152), (1152, 896), (640, 960), (960, 640),
            (1024, 1024), (704, 1088), (1088, 704)
        ]
    
    # CFGスケールを変える（7.0-9.0の範囲）
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    
    # サンプラーとスケジューラーを変える
    samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral"]
    schedulers = ["karras", "normal", "exponential", "sgm_uniform"]
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)
    
    width, height = random.choice(aspect_ratios)
    
    # 稀に解像度を微調整（±32ピクセル）
    if random.random() < 0.3:  # 30%の確率で微調整
        width_offset = random.choice([-32, -16, 0, 16, 32])
        height_offset = random.choice([-32, -16, 0, 16, 32])
        width = max(512, width + width_offset)
        height = max(512, height + height_offset)
    
    negative_prompt = generate_negative_prompt()
    
    print(f"[{i+1}/10] モデル: {model}")
    print(f"  プロンプト: {prompt[:120]}...")
    print(f"  解像度: {width}x{height}, ステップ: {steps}, CFG: {guidance_scale}")
    print(f"  サンプラー: {sampler}, スケジューラー: {scheduler}, seed: {seed}")
    
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
        "negative_prompt": negative_prompt,
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
print("  http://localhost:5559/api/job/<job_id>")
print()
print("生成された画像は以下で確認できます:")
print("  http://localhost:5559/api/images")
