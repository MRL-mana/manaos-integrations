#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナ好みのリアル系清楚系ギャル20枚生成（フェラなし・モデル追加・LoRA対応）"""

import requests
import json
import time
import sys
import io
import random
import hashlib
from pathlib import Path
import os

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"

# 利用可能なモデル（複数モデル対応）
COMFYUI_MODELS_DIR = Path(os.getenv("COMFYUI_MODELS_DIR", "C:/ComfyUI/models/checkpoints"))
MANA_MODELS_DIR = Path(os.getenv("MANA_MODELS_DIR", "C:/mana_workspace/models"))
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", str(Path.home() / "Downloads")))
PROJECT_MODELS_DIR = Path(__file__).parent / "models"  # プロジェクトルートのmodelsディレクトリ

# 利用可能なモデルを自動検出（複数ディレクトリから検索）
available_models = []
model_paths = {}  # モデル名 -> フルパスのマッピング

def add_models_from_dir(directory, description=""):
    """指定ディレクトリからモデルを追加"""
    if not directory.exists():
        return
    count = 0
    for model_file in directory.glob("*.safetensors"):
        model_name = model_file.name
        if model_name not in model_paths:
            available_models.append(model_name)
            model_paths[model_name] = str(model_file)
            count += 1
    for model_file in directory.glob("*.ckpt"):
        model_name = model_file.name
        if model_name not in model_paths:
            available_models.append(model_name)
            model_paths[model_name] = str(model_file)
            count += 1
    if count > 0 and description:
        print(f"  {description}: {count}件のモデルを検出")

# 1. ComfyUIのcheckpointsディレクトリから検出
add_models_from_dir(COMFYUI_MODELS_DIR, "ComfyUI checkpoints")

# 2. MANA_MODELS_DIRからも検出（シンボリックリンクやコピーがある場合）
add_models_from_dir(MANA_MODELS_DIR, "Mana workspace")

# 3. Downloadsフォルダから検出（CivitAIからダウンロードしたモデル）
add_models_from_dir(DOWNLOADS_DIR, "Downloads")

# 4. プロジェクトルートのmodelsディレクトリから検出
add_models_from_dir(PROJECT_MODELS_DIR, "Project models")

# 3. ComfyUI APIから利用可能なモデルリストを取得（オプション）
try:
    response = requests.get(f"{COMFYUI_URL}/object_info", timeout=5)
    if response.status_code == 200:
        object_info = response.json()
        checkpoint_loader = object_info.get("CheckpointLoaderSimple", {})
        if checkpoint_loader and "input" in checkpoint_loader:
            input_info = checkpoint_loader["input"]
            if "required" in input_info and "ckpt_name" in input_info["required"]:
                ckpt_info = input_info["required"]["ckpt_name"]
                if isinstance(ckpt_info, list) and len(ckpt_info) > 0:
                    api_models = ckpt_info[0]  # 通常はリストの最初の要素がモデルリスト
                    if isinstance(api_models, list):
                        for api_model in api_models:
                            if api_model not in available_models:
                                available_models.append(api_model)
except:
    pass  # APIが利用できない場合は無視

# 問題のあるモデルを除外（エラーが発生するモデル）
problematic_models = [
    "0482 dildo masturbation_v1_pony.safetensors",
    "0687 public indecency_v1_pony.safetensors",
    "ltx-2-19b-distilled.safetensors",  # LTX2は別のワークフローが必要な可能性
    "LTX-Video\\ltx-2-19b-distilled.safetensors",  # パス形式の問題
    "qqq-BDSM-v3-000010.safetensors",  # HTTP 400エラーが発生
    "ZIT_Amateur_Nudes_V2.safetensors",  # HTTP 400エラー
    "wan2.2_t2v_highnoise_masturbation_v1.0.safetensors",  # HTTP 400エラー（動画生成モデル）
    "waiIllustriousSDXL_v160.safetensors"  # HTTP 400エラー
]
# パス区切り文字を含むモデル名も除外
available_models = [m for m in available_models if m not in problematic_models and "\\" not in m and "/" not in m]

# モデルが見つからない場合はデフォルトを使用
if not available_models:
    available_models = ["realisian_v60.safetensors"]

# SD1.5/SDXL/SD3モデルを識別（モデル名から判定）
def is_sd15_model(model_name):
    """SD1.5モデルかどうかを判定"""
    # SDXL/SD3でない場合、デフォルトでSD1.5とみなす
    # ただし、明示的にSD1.5を示すキーワードがある場合は確実にSD1.5
    sd15_keywords = ["sd15", "sd-1.5", "sd 1.5", "1.5", "v1-5", "v1.5"]
    if any(keyword.lower() in model_name.lower() for keyword in sd15_keywords):
        return True
    # SDXL/SD3でなければSD1.5とみなす
    return not (is_sdxl_model(model_name) or is_sd3_model(model_name))

def is_sdxl_model(model_name):
    """SDXLモデルかどうかを判定"""
    sdxl_keywords = ["sdxl", "xl", "xlarge", "1024", "speciosa25D", "uwazumimix"]
    return any(keyword.lower() in model_name.lower() for keyword in sdxl_keywords)

def is_sd3_model(model_name):
    """SD3モデルかどうかを判定"""
    sd3_keywords = ["sd3", "sd-3", "flux", "stable-diffusion-3"]
    return any(keyword.lower() in model_name.lower() for keyword in sd3_keywords)

# 利用可能なLoRAを自動検出（画像生成用LoRAのみ）
COMFYUI_LORA_DIR = Path("C:/ComfyUI/models/loras")
available_loras = []
if COMFYUI_LORA_DIR.exists():
    for lora_file in COMFYUI_LORA_DIR.glob("*.safetensors"):
        lora_name = lora_file.name
        # Qwen系LoRA（画像生成用ではない）を除外
        if not any(keyword in lora_name.lower() for keyword in ["qwen", "llm", "text"]):
            available_loras.append(lora_name)
    for lora_file in COMFYUI_LORA_DIR.glob("*.ckpt"):
        lora_name = lora_file.name
        if not any(keyword in lora_name.lower() for keyword in ["qwen", "llm", "text"]):
            available_loras.append(lora_name)

MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure, malformed body, distorted body, broken body, twisted body, unnatural body, wrong proportions, asymmetrical body, bad body structure, malformed breasts, distorted breasts, wrong breast size, unnatural breasts, bad torso, malformed torso, distorted torso, bad waist, malformed waist, bad hips, malformed hips, bad legs, malformed legs, distorted legs, bad arms, malformed arms, distorted arms, extra fingers, missing fingers, bad fingers, extra toes, missing toes, bad toes, fused fingers, too many fingers, missing limbs, extra limbs, floating limbs, disconnected limbs, malformed hands, extra hands, missing hands, bad hands, malformed feet, extra feet, missing feet, bad feet, multiple people, other people, group, couple, oral sex, fellatio, blowjob, giving head, sucking cock, deep throat, performing oral, mouth sex, cock in mouth, penis in mouth"

def create_workflow(prompt, negative_prompt, model, lora_name=None, lora_strength=0.8, steps=70, guidance_scale=8.5, width=1024, height=1024, sampler="euler_ancestral", scheduler="karras", seed=1):
    """ComfyUIワークフローを作成（LoRA対応）"""
    workflow = {
        "1": {
            "inputs": {"ckpt_name": model},
            "class_type": "CheckpointLoaderSimple"
        }
    }
    
    # LoRAを追加（オプション）
    if lora_name:
        workflow["8"] = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["1", 0],
                "clip": ["1", 1]
            },
            "class_type": "LoraLoader"
        }
        model_output = ["8", 0]
        clip_output = ["8", 1]
    else:
        model_output = ["1", 0]
        clip_output = ["1", 1]
    
    workflow["2"] = {
        "inputs": {"text": prompt, "clip": clip_output},
        "class_type": "CLIPTextEncode"
    }
    workflow["3"] = {
        "inputs": {"text": negative_prompt, "clip": clip_output},
        "class_type": "CLIPTextEncode"
    }
    workflow["4"] = {
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": guidance_scale,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": model_output,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    }
    workflow["5"] = {
        "inputs": {"width": width, "height": height, "batch_size": 1},
        "class_type": "EmptyLatentImage"
    }
    workflow["6"] = {
        "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
        "class_type": "VAEDecode"
    }
    workflow["7"] = {
        "inputs": {"filename_prefix": "ComfyUI", "images": ["6", 0]},
        "class_type": "SaveImage"
    }
    return workflow

print("=" * 60)
print("マナ好みのリアル系清楚系ギャル30枚生成")
print("（女性一人・美しさ・魅力・引き締まった体・Dカップ・性行為・フェラなし・複数モデル・LoRA対応）")
print("=" * 60)
print()

print(f"利用可能なモデル数: {len(available_models)}")
if available_models:
    print("モデル一覧:")
    sd15_count = 0
    sdxl_count = 0
    sd3_count = 0
    for model in available_models[:10]:
        model_type = ""
        if is_sd3_model(model):
            model_type = " [SD3]"
            sd3_count += 1
        elif is_sdxl_model(model):
            model_type = " [SDXL]"
            sdxl_count += 1
        elif is_sd15_model(model):
            model_type = " [SD1.5]"
            sd15_count += 1
        print(f"  - {model}{model_type}")
    if len(available_models) > 10:
        print(f"  ... 他 {len(available_models) - 10} 件")
    print()
    print(f"モデルタイプ内訳: SD1.5={sum(1 for m in available_models if is_sd15_model(m))}件, "
          f"SDXL={sum(1 for m in available_models if is_sdxl_model(m))}件, "
          f"SD3={sum(1 for m in available_models if is_sd3_model(m))}件")

print()
print(f"利用可能なLoRA数: {len(available_loras)}")
if available_loras:
    print("LoRA一覧（画像生成用）:")
    for lora in available_loras[:10]:
        print(f"  - {lora}")
    if len(available_loras) > 10:
        print(f"  ... 他 {len(available_loras) - 10} 件")
    print()
    print("※ LoRAは30%の確率でランダムに適用されます")
else:
    print("  （画像生成用LoRAが見つかりませんでした）")
print()
print("注意: A1111は別のソフトウェアです。ComfyUIでは使用できません。")
print("      SDXL/SD3モデルは自動的に検出され、適切な解像度で生成されます。")
print()

# マナ好みの清楚系ギャルの要素（美しさと魅力を強調・この子がタイプのスタイル）
expressions = ["innocent eyes", "clear eyes", "bright eyes", "sparkling eyes", "pure eyes", "gentle eyes", "wide eyes", "big eyes", "beautiful eyes", "captivating eyes", "charming eyes", "large eyes", "round eyes", "doll-like eyes", "coy expression", "shy expression"]
faces = ["beautiful face", "cute face", "innocent face", "pure face", "refined face", "neat face", "well-defined face", "pretty face", "attractive face", "gorgeous face", "stunning face", "perfect face", "flawless face", "elegant face", "round face", "doll-like face", "fair skin", "smooth skin", "slight blush"]
# 引き締まった体とDカップを強調（マナ好み）
bodies = ["toned body", "fit body", "athletic body", "slim toned body", "well-toned body", "muscular toned body", "defined body", "perfect body", "ideal body", "beautiful body", "sexy body", "alluring body"]
breast_size = ["D cup", "D-cup breasts", "medium breasts", "proportional breasts", "perfect breasts", "beautiful breasts", "natural breasts"]
# 性行為シーン（フェラなし）
poses = ["standing", "sitting", "lying down", "cowgirl position", "missionary position", "doggy style", "69 position", "reverse cowgirl", "spread legs", "legs spread"]
scenes = ["during sex", "sexual act", "intimate moment", "making love", "having sex", "passionate moment", "romantic scene", "erotic scene"]
sex_acts = ["sexual intercourse", "sex act", "having sex", "during sex", "making love", "penetration", "sexual activity"]
hair_styles = ["long straight hair", "long wavy hair", "bob cut", "shoulder length hair", "ponytail", "twintails", "curly hair", "short hair", "hair bun", "hair partially tied up", "loose strands", "straight bangs"]
makeup = ["natural makeup", "light makeup", "minimal makeup", "fresh makeup", "soft makeup", "cute makeup", "subtle makeup", "defined eyelashes"]
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style", "sweet gyaru style", "gyaru fashion"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting", "studio lighting", "romantic lighting", "bright lighting", "sunny day", "daylight"]
backgrounds = ["bedroom", "bed", "hotel room", "intimate setting", "private room", "romantic atmosphere", "luxury room", "urban setting", "outdoor", "public space", "street", "city"]

prompt_ids = []

for i in range(30):
    model = random.choice(available_models)
    
    # LoRAをランダムに使用（30%の確率で使用）
    lora_name = None
    lora_strength = None
    if available_loras and random.random() < 0.3:
        lora_name = random.choice(available_loras)
        lora_strength = round(random.uniform(0.5, 1.0), 2)
    
    # マナ好みのリアル系清楚系ギャルプロンプト（女性一人・美しさ・魅力・身体崩れ防止・引き締まった体・Dカップ・性行為・フェラなし・この子がタイプのスタイル）
    prompt_parts = [
        "Japanese", "Japanese woman", "1girl", "solo", "alone", "single woman",  # 女性一人を強調
        random.choice(clothing_style),
        "naked", random.choice(poses),
        random.choice(expressions),
        random.choice(faces),
        random.choice(bodies),  # 引き締まった体（マナ好み）
        random.choice(breast_size),  # Dカップ
        "perfect proportions", "well-proportioned body", "natural proportions", "ideal proportions",
        "correct anatomy", "perfect anatomy", "accurate anatomy", "flawless anatomy",
        "natural body structure", "proper body structure", "beautiful body structure",
        "beautiful", "gorgeous", "stunning", "attractive", "sexy", "alluring", "captivating", "charming",
        random.choice(scenes),  # 性行為シーン
        random.choice(sex_acts),  # 性行為
        random.choice(hair_styles),
        random.choice(makeup),
        random.choice(lighting),
        random.choice(backgrounds),
        "realistic", "photorealistic", "real photo", "photography",
        "high quality", "masterpiece", "best quality", "ultra quality", "perfect quality",
        "detailed", "sharp focus", "8k uhd", "ultra detailed", "professional photography",
        "beautiful skin", "smooth skin", "flawless skin", "perfect skin",
        "no body distortion", "no deformation", "no malformation",
        "aesthetic", "artistic", "elegant", "refined",
        "no multiple people", "no other people", "only one person",  # 一人であることを強調
        "doll-like", "anime-inspired", "gyaru aesthetic"  # この子がタイプのスタイル要素
    ]
    prompt = ", ".join(prompt_parts)
    
    # マナ好みの高品質パラメータ（身体崩れ防止・美しさ重視）
    # SDXL/SD3モデルの場合は解像度を調整
    if is_sdxl_model(model) or is_sd3_model(model):
        steps = random.choice([50, 55, 60, 65])
        width, height = random.choice([
            (1024, 1024), (1024, 1280), (1280, 1024), (1152, 1344), (1344, 1152)
        ])
    else:
        steps = random.choice([60, 65, 70, 75])
        width, height = random.choice([
            (768, 1024), (1024, 768), (832, 1216), (896, 1152), 
            (960, 1280), (1024, 1024), (896, 1280)
        ])
    
    guidance_scale = round(random.uniform(8.0, 9.5), 1)
    sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])
    scheduler = random.choice(["normal", "karras", "exponential"])
    
    model_hash = int(hashlib.md5(model.encode()).hexdigest()[:8], 16)
    prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    time_seed = int(time.time() * 1000000) % (2**32)
    random_seed = random.randint(1, 2**32 - 1)
    seed = (time_seed ^ random_seed ^ model_hash ^ prompt_hash ^ i) % (2**32)
    
    workflow = create_workflow(
        prompt=prompt,
        negative_prompt=MUFUFU_NEGATIVE_PROMPT,
        model=model,
        lora_name=lora_name,
        lora_strength=lora_strength,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed
    )
    
    lora_info = f" + LoRA:{lora_name[:30]}" if lora_name else ""
    print(f"[{i+1:2d}/30] {model[:40]}{lora_info}")
    print(f"  {prompt[:70]}...")
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
                print(f"  [ERROR] プロンプトIDが返されませんでした")
        else:
            print(f"  [HTTP {response.status_code}]")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    if i < 29:
        time.sleep(0.3)

print()
print("=" * 60)
print(f"送信完了: {len(prompt_ids)}件")
print("=" * 60)

if len(prompt_ids) > 0:
    print()
    print("プロンプトID一覧:")
    for i, prompt_id in enumerate(prompt_ids, 1):
        print(f"  {i:2d}. {prompt_id}")
    
    print()
    print("画像生成の進行状況を確認中...")
    print("（生成には時間がかかります）")
    print()
    print("生成状況の確認:")
    print("  python check_20_mana_no_fellatio.py")
