#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""20枚の画像を生成（プロンプトと設定を毎回変える）"""

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

# プロンプト要素のバリエーション（大幅に拡充）
poses = [
    "sitting", "lying down", "standing", "kneeling", "bent over",
    "on all fours", "spread legs", "arms up", "back arch", "side view",
    "cowgirl position", "missionary position", "doggy style", "69 position",
    "squatting", "leaning forward", "legs spread wide", "arms behind back",
    "lying on back", "lying on stomach", "sitting on floor", "standing against wall",
    "kneeling on bed", "bent over bed", "legs in air", "one leg up",
    "spread eagle", "reverse cowgirl", "standing doggy", "sitting reverse"
]
expressions = [
    "smile", "innocent look", "seductive expression", "pleasure face",
    "blushing", "winking", "open mouth", "tongue out", "closed eyes",
    "looking at viewer", "ecstatic expression", "moaning", "ahegao",
    "teary eyes", "lustful expression", "shy expression", "surprised expression",
    "sultry look", "dreamy eyes", "half-closed eyes", "looking away",
    "kiss face", "panting", "sweating", "red face"
]
styles = [
    "clear and pure gyaru style", "cute gyaru", "innocent gyaru",
    "sexy gyaru", "kawaii gyaru", "pure gyaru", "clear gyaru style",
    "gyaru style", "gyaru fashion", "gal style", "gyaru makeup",
    "gyaru-kei", "onee gyaru", "agejo gyaru", "hime gyaru"
]
scenes = [
    "sexual act", "intimate moment", "erotic scene", "passionate moment",
    "intimate scene", "erotic act", "passionate act", "intimate act",
    "making love", "having sex", "foreplay", "oral sex", "penetration",
    "masturbation", "orgasm", "climax", "afterglow", "during sex",
    "passionate embrace", "intimate position", "erotic position"
]
hair_styles = [
    "long hair", "short hair", "medium hair", "ponytail", "twin tails",
    "messy hair", "straight hair", "wavy hair", "curly hair", "bob cut",
    "hair down", "hair up", "side ponytail", "braided hair", "hair bun"
]
body_types = [
    "slim body", "petite body", "curvy body", "athletic body", "soft body",
    "slender waist", "wide hips", "small breasts", "medium breasts", "large breasts",
    "long legs", "smooth skin", "pale skin", "tanned skin", "fair skin"
]
lighting = [
    "natural lighting", "soft lighting", "dramatic lighting", "warm lighting",
    "cool lighting", "rim lighting", "backlighting", "side lighting",
    "dim lighting", "bright lighting", "candlelight", "sunlight",
    "moonlight", "neon lighting", "studio lighting"
]
backgrounds = [
    "bedroom", "bed", "sofa", "bathroom", "shower", "bathtub", "hotel room",
    "beach", "forest", "outdoor", "indoor", "dark room", "bright room",
    "minimalist background", "simple background", "blurred background"
]
camera_angles = [
    "close-up", "medium shot", "full body", "upper body", "lower body",
    "from above", "from below", "from side", "from front", "from behind",
    "low angle", "high angle", "eye level", "dutch angle", "wide angle"
]
qualities = [
    "high quality", "detailed", "masterpiece", "best quality",
    "ultra detailed", "8k", "photorealistic", "cinematic lighting",
    "professional photography", "sharp focus", "perfect anatomy",
    "high resolution", "4k", "detailed face", "detailed body"
]

# 身体構造を強化するタグ（必ず含める、大幅に拡充）
anatomy_tags = [
    "perfect anatomy", "correct anatomy", "proper proportions",
    "well-proportioned body", "natural body", "realistic body structure",
    "anatomically correct", "correct body structure", "proper body structure",
    "natural proportions", "realistic proportions", "correct proportions",
    "well-structured body", "natural body structure", "proper anatomy",
    "perfect body structure", "correct body proportions", "natural body proportions",
    "realistic anatomy", "accurate anatomy", "proper body anatomy",
    "well-formed body", "correctly proportioned", "natural body shape",
    "realistic body shape", "proper skeletal structure", "correct bone structure",
    "natural joints", "proper limb proportions", "correct torso proportions",
    "natural waist", "proper hip structure", "correct leg proportions",
    "natural arm proportions", "proper shoulder structure", "correct neck proportions"
]

# ネガティブプロンプトの追加要素（バリエーション、身体構造を大幅強化）
negative_additions = [
    "bad hands", "bad anatomy", "blurry", "low quality",
    "worst quality", "normal quality", "jpeg artifacts",
    "watermark", "signature", "username", "text",
    "duplicate", "ugly", "deformed", "poorly drawn",
    "bad proportions", "extra limbs", "disfigured",
    "mutation", "mutated", "mutilated", "bad art",
    "bad structure", "out of frame", "cropped",
    "missing fingers", "extra digit", "fewer digits",
    # 身体構造に関する大幅強化
    "deformed body", "broken body", "twisted body", "distorted body",
    "malformed body", "incorrect anatomy", "wrong proportions",
    "unnatural body", "broken limbs", "twisted limbs",
    "extra arms", "extra legs", "missing limbs", "disconnected limbs",
    "floating limbs", "broken joints", "unnatural pose", "impossible pose",
    "distorted proportions", "unnatural proportions", "broken anatomy",
    "twisted anatomy", "malformed anatomy", "incorrect body structure",
    "broken body structure", "distorted body structure",
    # さらに追加
    "deformed limbs", "broken bones", "twisted spine", "distorted torso",
    "malformed joints", "incorrect bone structure", "wrong body shape",
    "unnatural curves", "broken symmetry", "distorted symmetry",
    "asymmetric body", "uneven proportions", "disproportionate body",
    "unnatural body shape", "wrong body structure", "broken body parts",
    "distorted body parts", "malformed body parts", "incorrect body parts",
    "twisted body parts", "broken body anatomy", "distorted body anatomy",
    "malformed body anatomy", "incorrect skeletal structure", "broken skeletal structure",
    "distorted skeletal structure", "unnatural skeletal structure", "wrong skeletal structure"
]

# サンプラーとスケジューラーのバリエーション
samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpm_fast", "lms"]
schedulers = ["karras", "normal", "exponential", "sgm_uniform"]

def generate_negative_prompt():
    """バリエーションのあるネガティブプロンプトを生成（身体構造を大幅強化）"""
    base_negative = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume"
    # 身体構造に関する要素を必ず多く含める
    anatomy_negatives = [
        "bad anatomy", "deformed body", "broken body", "twisted body",
        "distorted body", "incorrect anatomy", "wrong proportions",
        "unnatural body", "broken limbs", "extra limbs",
        "deformed limbs", "broken bones", "twisted spine", "distorted torso",
        "malformed joints", "incorrect bone structure", "wrong body shape",
        "unnatural curves", "broken symmetry", "distorted symmetry",
        "asymmetric body", "uneven proportions", "disproportionate body"
    ]
    # 身体構造のネガティブを5-8個必ず含める（大幅に増加）
    selected_anatomy = random.sample(anatomy_negatives, k=random.randint(5, 8))
    # その他のネガティブ要素
    other_negatives = [n for n in negative_additions if n not in anatomy_negatives]
    additional_others = ", ".join(random.sample(other_negatives, k=random.randint(8, 15)))
    return f"{base_negative}, {', '.join(selected_anatomy)}, {additional_others}"

def generate_varied_prompt():
    """バリエーション豊かなプロンプトを生成（身体構造を強化、完全にランダム化）"""
    # 基本要素をランダムに選択（複数選択可能なものは複数選択）
    style = random.choice(styles)
    pose = random.choice(poses)
    # ポーズを2つ選ぶ場合もある
    if random.random() < 0.3:
        pose2 = random.choice([p for p in poses if p != pose])
        pose = f"{pose}, {pose2}"

    expression = random.choice(expressions)
    # 表情を2つ選ぶ場合もある
    if random.random() < 0.3:
        expr2 = random.choice([e for e in expressions if e != expression])
        expression = f"{expression}, {expr2}"

    scene = random.choice(scenes)
    # シーンを2つ選ぶ場合もある
    if random.random() < 0.2:
        scene2 = random.choice([s for s in scenes if s != scene])
        scene = f"{scene}, {scene2}"

    # 髪型を複数選ぶ場合もある
    hair = random.choice(hair_styles)
    if random.random() < 0.2:
        hair2 = random.choice([h for h in hair_styles if h != hair])
        hair = f"{hair}, {hair2}"

    # 体型を複数選ぶ場合もある
    body = random.choice(body_types)
    if random.random() < 0.3:
        body2 = random.choice([b for b in body_types if b != body])
        body = f"{body}, {body2}"

    lighting_elem = random.choice(lighting)
    # ライティングを2つ選ぶ場合もある
    if random.random() < 0.2:
        light2 = random.choice([l for l in lighting if l != lighting_elem])
        lighting_elem = f"{lighting_elem}, {light2}"

    background = random.choice(backgrounds)
    angle = random.choice(camera_angles)

    # 品質タグを複数選択（3-6個）
    quality_tags = random.sample(qualities, k=random.randint(3, 6))

    # 身体構造タグを必ず3-5個含める（大幅に増加）
    anatomy_tag = random.sample(anatomy_tags, k=random.randint(3, 5))

    # 追加の詳細要素（ランダムに追加）
    additional_details = []
    detail_options = [
        "sweat", "wet", "glossy skin", "smooth skin", "soft skin",
        "detailed eyes", "detailed face", "detailed hands", "detailed feet",
        "realistic", "photorealistic", "natural", "lifelike",
        "beautiful", "attractive", "charming", "elegant", "graceful"
    ]
    if random.random() < 0.7:  # 70%の確率で追加
        num_details = random.randint(1, 3)
        additional_details = random.sample(detail_options, k=num_details)

    # プロンプトのパーツを完全にランダムな順序で組み立て
    # 身体構造タグを先頭に配置（重要度を高める）
    prompt_parts = [
        ", ".join(anatomy_tag[:2]),  # 身体構造タグを先頭に2個
        style,
        f"naked, {pose}",
        expression,
        scene,
        hair,
        body,
        lighting_elem,
        f"in {background}",
        angle,
        ", ".join(anatomy_tag[2:]),  # 残りの身体構造タグ
        ", ".join(quality_tags)
    ]

    # 追加の詳細要素がある場合は追加
    if additional_details:
        prompt_parts.insert(random.randint(4, len(prompt_parts) - 1), ", ".join(additional_details))

    # 順序を完全にランダムにシャッフル（身体構造タグの最初の2個だけは先頭に固定）
    anatomy_start = prompt_parts[0]
    rest_parts = prompt_parts[1:]
    random.shuffle(rest_parts)

    # 完全にランダムな順序にする（身体構造タグを先頭に固定）
    final_parts = [anatomy_start] + rest_parts

    # さらにランダムにシャッフル（ただし身体構造タグは先頭に残す）
    if random.random() < 0.3:  # 30%の確率でさらにシャッフル
        # 身体構造タグ以外をシャッフル
        anatomy_part = final_parts[0]
        other_parts = final_parts[1:]
        random.shuffle(other_parts)
        final_parts = [anatomy_part] + other_parts

    return ", ".join(final_parts)

print("=" * 60)
print("30枚の画像を生成します（プロンプトと設定を毎回変える）")
print("要素: 日本人、清楚系ギャル、裸、可愛い系ギャル、性行為")
print("=" * 60)
print()

job_ids = []

for i in range(30):
    model = random.choice(all_models)
    prompt = generate_varied_prompt()

    # 毎回完全に異なるパラメータを設定（完全ランダムシード、さらに強化）
    # 時間、ランダム値、インデックス、モデル名のハッシュ、プロンプトのハッシュを組み合わせて完全にユニークなシードを生成
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    uuid_hash = int(hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    index_seed = (i * 7919) % (2**32)  # 素数を使ったインデックスベースのシード
    microsecond_seed = int((time.time() % 1) * 1000000) % (2**32)  # マイクロ秒レベルの精度
    seed = (time_seed ^ random_seed ^ index_seed ^ model_hash ^ prompt_hash ^ uuid_hash ^ microsecond_seed) % (2**32)

    # モデルに応じてステップ数を調整（身体構造を改善するため、より多めに）
    if model in sdxl_models:
        steps = random.choice([50, 55, 60, 65, 70])  # 身体構造改善のため50-70に
        aspect_ratios = [
            (1024, 1024),  # 正方形
            (1024, 1280),  # 縦長
            (1280, 1024),  # 横長
            (1152, 1152),  # 少し小さい正方形
            (1024, 1536),  # より縦長
            (1536, 1024),  # より横長
            (1088, 1088),  # 別の正方形サイズ
            (1216, 1216),  # 別の正方形サイズ
            (960, 1344),   # 縦長バリエーション
            (1344, 960),   # 横長バリエーション
        ]
    else:
        steps = random.choice([45, 50, 55, 60, 65])  # 身体構造改善のため45-65に
        aspect_ratios = [
            (768, 1024),  # 縦長
            (1024, 768),  # 横長
            (832, 1216),  # より縦長
            (1216, 832),  # より横長
            (896, 1152),  # 中程度の縦長
            (1152, 896),  # 中程度の横長
            (640, 960),   # より小さい縦長
            (960, 640),   # より小さい横長
            (1024, 1024), # 正方形も追加
            (704, 1088),  # 別の縦長
            (1088, 704),  # 別の横長
        ]

    # CFGスケールを身体構造に良い範囲に（7.0-9.0の範囲、身体構造に良い値）
    guidance_scale = round(random.uniform(7.0, 9.0), 1)
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)
    width, height = random.choice(aspect_ratios)

    # 稀に解像度を微調整（±32ピクセル）
    if random.random() < 0.2:  # 20%の確率で微調整
        width_offset = random.choice([-32, -16, 0, 16, 32])
        height_offset = random.choice([-32, -16, 0, 16, 32])
        width = max(512, width + width_offset)
        height = max(512, height + height_offset)
    negative_prompt = generate_negative_prompt()

    print(f"[{i+1}/30] モデル: {model}")
    print(f"  プロンプト: {prompt[:100]}...")  # 長い場合は省略
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
        "negative_prompt": negative_prompt,  # カスタムネガティブプロンプト
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
    if i < 29:
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
