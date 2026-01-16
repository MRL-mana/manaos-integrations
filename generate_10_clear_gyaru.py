#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清楚系ギャル10枚生成（プロンプトと設定を毎回変える）"""

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
sdxl_models = [
    "speciosa25D_v12.safetensors",  # 6.62 GB
    "uwazumimixILL_v50.safetensors"  # 6.46 GB
]

other_models = [
    "realisian_v60.safetensors",  # 2.14 GB
    "realisticVisionV60B1_v51HyperVAE.safetensors",  # SD 1.5ベース
    "speciosaRealistica_v12b.safetensors",  # 1.13 GB
    "shibari_v20.safetensors",  # 0.04 GB
    "qqq-BDSM-v3-000010.safetensors",  # 0.04 GB
    "0482 dildo masturbation_v1_pony.safetensors",  # 0.16 GB
    "0687 public indecency_v1_pony.safetensors"  # 0.16 GB
]

all_models = sdxl_models + other_models

# 基本要件の要素
base_elements = {
    "nationality": ["Japanese", "日本人", "Japanese woman"],
    "style": ["clear and pure gyaru style", "cute gyaru", "innocent gyaru", "clear gyaru style", "pure gyaru"],
    "naked": ["naked", "nude", "no clothes"],
    "eyes": ["big eyes", "wide eyes", "パッチリした目", "large eyes", "beautiful eyes", "sparkling eyes", "bright eyes"],
    "face": ["beautiful face", "well-proportioned face", "perfect face", "整った顔", "symmetrical face", "attractive face", "cute face"],
    "body": ["toned body", "fit body", "引き締まった体", "slim and toned", "athletic body", "well-defined body", "muscular definition"],
    "sexual_act": ["sexual act", "intimate moment", "during sex", "making love", "passionate moment", "erotic scene", "intimate scene"]
}

# 追加バリエーション要素
additional_poses = [
    "cowgirl position", "missionary position", "doggy style", "69 position",
    "sitting", "lying down", "kneeling", "bent over", "on all fours",
    "spread legs", "legs spread wide", "arms up", "back arch",
    "reverse cowgirl", "standing doggy", "squatting", "leaning forward"
]

additional_expressions = [
    "pleasure face", "blushing", "moaning", "ecstatic expression",
    "lustful expression", "teary eyes", "sweating", "panting",
    "closed eyes", "half-closed eyes", "looking at viewer", "looking away"
]

additional_hair = [
    "long hair", "short hair", "medium hair", "ponytail", "twin tails",
    "straight hair", "wavy hair", "curly hair", "bob cut", "messy hair"
]

additional_body_details = [
    "smooth skin", "glossy skin", "wet", "sweat", "fair skin", "pale skin",
    "slender waist", "wide hips", "long legs", "small breasts", "medium breasts", "large breasts"
]

additional_scenes = [
    "in bedroom", "on bed", "in bathroom", "in shower", "in bathtub",
    "in hotel room", "in dark room", "in bright room"
]

additional_lighting = [
    "natural lighting", "soft lighting", "dramatic lighting", "warm lighting",
    "dim lighting", "bright lighting", "studio lighting", "moonlight"
]

additional_camera = [
    "close-up", "medium shot", "full body", "upper body", "lower body",
    "from above", "from below", "from side", "from front", "from behind",
    "low angle", "high angle", "eye level"
]

additional_qualities = [
    "high quality", "detailed", "masterpiece", "best quality",
    "ultra detailed", "8k", "photorealistic", "cinematic lighting",
    "sharp focus", "perfect anatomy", "high resolution", "4k"
]

# 身体構造を強化するタグ
anatomy_tags = [
    "perfect anatomy", "correct anatomy", "proper proportions",
    "well-proportioned body", "natural body", "realistic body structure",
    "anatomically correct", "correct body structure", "proper body structure",
    "natural proportions", "realistic proportions", "correct proportions",
    "well-structured body", "natural body structure", "proper anatomy"
]

# ネガティブプロンプトの追加要素
negative_additions = [
    "bad hands", "bad anatomy", "blurry", "low quality",
    "worst quality", "normal quality", "jpeg artifacts",
    "watermark", "signature", "username", "text",
    "duplicate", "ugly", "deformed", "poorly drawn",
    "bad proportions", "extra limbs", "disfigured",
    "mutation", "mutated", "mutilated", "bad art",
    "bad structure", "out of frame", "cropped",
    "missing fingers", "extra digit", "fewer digits",
    "deformed body", "broken body", "twisted body", "distorted body",
    "malformed body", "incorrect anatomy", "wrong proportions",
    "unnatural body", "broken limbs", "twisted limbs",
    "extra arms", "extra legs", "missing limbs", "disconnected limbs",
    "floating limbs", "broken joints", "unnatural pose", "impossible pose"
]

def generate_negative_prompt():
    """バリエーションのあるネガティブプロンプトを生成"""
    base_negative = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume"
    anatomy_negatives_core = [
        "bad anatomy", "deformed body", "broken body", "twisted body",
        "distorted body", "incorrect anatomy", "wrong proportions",
        "unnatural body", "broken limbs", "extra limbs",
        "malformed body", "incorrect bone structure", "unnatural joints"
    ]
    selected_anatomy = random.sample(anatomy_negatives_core, k=random.randint(5, 8))
    other_negatives = [n for n in negative_additions if n not in anatomy_negatives_core]
    additional_others = ", ".join(random.sample(other_negatives, k=random.randint(5, 10)))
    return f"{base_negative}, {', '.join(selected_anatomy)}, {additional_others}"

def generate_varied_prompt():
    """バリエーション豊かなプロンプトを生成（基本要件 + 追加要素）"""
    # 基本要件から各要素をランダムに選択
    nationality = random.choice(base_elements["nationality"])
    style = random.choice(base_elements["style"])
    naked = random.choice(base_elements["naked"])
    eyes = random.choice(base_elements["eyes"])
    if random.random() < 0.4:  # 40%の確率で2つ目の目タグを追加
        eyes2 = random.choice([e for e in base_elements["eyes"] if e != eyes])
        eyes = f"{eyes}, {eyes2}"

    face = random.choice(base_elements["face"])
    if random.random() < 0.3:  # 30%の確率で2つ目の顔タグを追加
        face2 = random.choice([f for f in base_elements["face"] if f != face])
        face = f"{face}, {face2}"

    body = random.choice(base_elements["body"])
    if random.random() < 0.4:  # 40%の確率で2つ目の体タグを追加
        body2 = random.choice([b for b in base_elements["body"] if b != body])
        body = f"{body}, {body2}"

    sexual_act = random.choice(base_elements["sexual_act"])

    # 追加要素をランダムに選択
    pose = random.choice(additional_poses)
    if random.random() < 0.3:
        pose2 = random.choice([p for p in additional_poses if p != pose])
        pose = f"{pose}, {pose2}"

    expression = random.choice(additional_expressions)
    if random.random() < 0.3:
        expr2 = random.choice([e for e in additional_expressions if e != expression])
        expression = f"{expression}, {expr2}"

    hair = random.choice(additional_hair)
    body_details = random.sample(additional_body_details, k=random.randint(2, 4))
    scene = random.choice(additional_scenes)
    lighting_elem = random.choice(additional_lighting)
    camera = random.choice(additional_camera)
    qualities = random.sample(additional_qualities, k=random.randint(3, 5))
    anatomy = random.sample(anatomy_tags, k=random.randint(2, 4))

    # プロンプトのパーツを組み立て（順序をランダム化）
    prompt_parts = [
        nationality,
        style,
        naked,
        eyes,
        face,
        body,
        sexual_act,
        pose,
        expression,
        hair,
        ", ".join(body_details),
        scene,
        lighting_elem,
        camera,
        ", ".join(anatomy),
        ", ".join(qualities)
    ]

    # 順序をランダムにシャッフル（最初のnationalityとstyleは固定、他はランダム）
    fixed_start = [prompt_parts[0], prompt_parts[1]]  # nationality, style
    remaining = prompt_parts[2:]
    random.shuffle(remaining)

    final_parts = fixed_start + remaining

    return ", ".join(final_parts)

print("=" * 60)
print("10枚の画像を生成します（清楚系ギャル・裸・パッチリ目・整った顔・引き締まった体・性行為中）")
print("プロンプトと設定を毎回変えて、同じ画像が生成されないようにします")
print("=" * 60)
print()

job_ids = []

for i in range(10):
    # モデルをランダムに選択
    model = random.choice(all_models)

    # プロンプトを生成
    prompt = generate_varied_prompt()

    # 完全にユニークなシードを生成
    unique_string = f"{uuid.uuid4()}-{prompt}-{time.time_ns()}-{model}-{i}"
    seed = int(hashlib.sha256(unique_string.encode()).hexdigest(), 16) % (2**32)

    # モデルに応じてステップ数と解像度を調整
    if model in sdxl_models:
        steps = random.choice([50, 55, 60, 65, 70])
        aspect_ratios = [
            (1024, 1024), (1024, 1280), (1280, 1024),
            (1152, 1152), (1024, 1536), (1536, 1024),
            (1088, 1088), (1216, 1216)
        ]
    else:
        steps = random.choice([45, 50, 55, 60, 65])
        aspect_ratios = [
            (768, 1024), (1024, 768), (832, 1216), (1216, 832),
            (896, 1152), (1152, 896), (640, 960), (960, 640),
            (1024, 1024), (704, 1088), (1088, 704)
        ]

    # CFGスケールをランダムに設定
    guidance_scale = round(random.uniform(7.0, 9.0), 1)

    # サンプラーとスケジューラーをランダムに選択
    samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral",
                "dpm_2", "dpm_2_ancestral", "dpm_fast", "lms", "dpmpp_sde"]
    schedulers = ["karras", "normal", "exponential", "sgm_uniform", "simple"]
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)

    # 解像度を選択
    width, height = random.choice(aspect_ratios)

    # 稀に解像度を微調整（±32ピクセル）
    if random.random() < 0.3:
        width_offset = random.choice([-32, -16, 0, 16, 32])
        height_offset = random.choice([-32, -16, 0, 16, 32])
        width = max(512, width + width_offset)
        height = max(512, height + height_offset)

    # ネガティブプロンプトを生成
    negative_prompt = generate_negative_prompt()

    # リクエストデータ
    data = {
        "prompt": prompt,
        "model": model,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "width": width,
        "height": height,
        "sampler": sampler,
        "scheduler": scheduler,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "mufufu_mode": True
    }

    print(f"[{i+1}/10] モデル: {model}")
    print(f"  プロンプト: {prompt[:80]}...")
    print(f"  解像度: {width}x{height}, ステップ: {steps}, CFG: {guidance_scale}")
    print(f"  サンプラー: {sampler}, スケジューラー: {scheduler}, seed: {seed}")

    try:
        response = requests.post(GALLERY_API, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                job_ids.append((job_id, model))
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")

    print()

    # リクエスト間隔を空ける
    if i < 9:
        time.sleep(2)

print("=" * 60)
print(f"[完了] {len(job_ids)}件の画像生成ジョブを送信しました")
print("=" * 60)
print()

if job_ids:
    print("ジョブID一覧:")
    for idx, (job_id, model) in enumerate(job_ids, 1):
        print(f"  {idx}. {job_id} ({model})")
    print()
    print("画像生成の進行状況は以下で確認できます:")
    print("  http://localhost:5559/api/job/<job_id>")
    print()
    print("生成された画像は以下で確認できます:")
    print("  http://localhost:5559/api/images")
