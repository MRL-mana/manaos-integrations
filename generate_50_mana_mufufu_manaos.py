#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マナごのみ画像生成スクリプト（評価・学習機能統合版）
"""

import requests
import json
import time
import sys
import io
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

if sys.platform == 'win32':
    # PowerShellのパイプ等でstdoutが壊れないようにガード
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

COMFYUI_URL = "http://localhost:8188"
EVALUATION_DB = Path("C:/ComfyUI/input/mana_favorites/evaluation.json")
GENERATION_METADATA_DB = Path("C:/ComfyUI/input/mana_favorites/generation_metadata.json")
OUTPUT_DIR = Path("C:/ComfyUI/output")

# モデルとLoRAの検出
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
        # 露骨な成人向け（性行為・性器・BDSM等）のLoRAは除外（安全側に倒す）
        excluded_lora_keywords = [
            "qwen", "llm", "text",
            "nsfw", "nude", "nudity",
            "sex", "intercourse", "porn",
            "bdsm", "dildo", "masturb",
            "penis", "pussy", "cum",
            "public indecency",
            "rape", "incest",
        ]
        if not any(kw in lora_name.lower() for kw in excluded_lora_keywords):
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


def learn_from_evaluations() -> Dict:
    """
    評価データから好みを学習

    Returns:
        学習された好み（モデル、LoRA、パラメータ）
    """
    learned = {
        "models": [],
        "loras": [],
        "params": {
            "steps": [],
            "guidance_scale": [],
            "width": [],
            "height": [],
            "sampler": [],
            "scheduler": []
        }
    }

    # 評価データと生成メタデータを読み込み
    evaluations = {}
    generation_metadata = {}

    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, 'r', encoding='utf-8') as f:
                evaluations = json.load(f)
        except Exception as e:
            print(f"⚠️ 評価データの読み込みエラー: {e}")

    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, 'r', encoding='utf-8') as f:
                generation_metadata = json.load(f)
        except Exception as e:
            print(f"⚠️ 生成メタデータの読み込みエラー: {e}")

    if not evaluations or not generation_metadata:
        return learned

    # 高評価画像（スコア1-2）を特定
    high_score_images = []
    for img_path, eval_data in evaluations.items():
        score = eval_data.get("score", 0)
        if score <= 2:  # 高評価
            high_score_images.append(img_path)

    if not high_score_images:
        return learned

    # 高評価画像に使用されたモデル、LoRA、パラメータを抽出
    matched_count = 0
    learned_models = {}
    learned_loras = {}
    learned_params = {
        "steps": [],
        "guidance_scale": [],
        "width": [],
        "height": [],
        "sampler": [],
        "scheduler": []
    }

    for img_path in high_score_images:
        img_name = Path(img_path).name
        img_path_str = str(img_path)
        matched = False

        # 生成メタデータから該当する画像を探す
        for gen_id, gen_data in generation_metadata.items():
            # 1. output_pathsリストをチェック（最も正確）
            output_paths = gen_data.get("output_paths", [])
            if output_paths:
                for output_path in output_paths:
                    if str(output_path) == img_path_str or Path(output_path).name == img_name:
                        matched = True
                        break
                if matched:
                    pass  # 下の処理に進む

            # 2. output_filenamesリストをチェック
            if not matched:
                output_filenames = gen_data.get("output_filenames", [])
                if output_filenames:
                    for output_filename in output_filenames:
                        if output_filename == img_name or img_name in output_filename:
                            matched = True
                            break

            # 3. 単一のoutput_filenameをチェック（後方互換性）
            if not matched:
                output_filename = gen_data.get("output_filename", "")
                if output_filename:
                    if output_filename == img_name or output_filename.endswith(img_name) or img_name in output_filename:
                        matched = True

            # 4. output_pathをチェック（後方互換性）
            if not matched:
                output_path = gen_data.get("output_path", "")
                if output_path:
                    if str(output_path) == img_path_str or Path(output_path).name == img_name:
                        matched = True

            if matched:
                matched_count += 1
                # モデルを記録
                model = gen_data.get("model", "")
                if model:
                    learned_models[model] = learned_models.get(model, 0) + 1

                # LoRAを記録
                loras = gen_data.get("loras", [])
                for lora in loras:
                    lora_name = lora.get("name", "") if isinstance(lora, dict) else str(lora)
                    if lora_name:
                        learned_loras[lora_name] = learned_loras.get(lora_name, 0) + 1

                # パラメータを記録
                learned_params["steps"].append(gen_data.get("steps", 50))
                learned_params["guidance_scale"].append(gen_data.get("guidance_scale", 8.0))
                learned_params["width"].append(gen_data.get("width", 1024))
                learned_params["height"].append(gen_data.get("height", 1024))
                learned_params["sampler"].append(gen_data.get("sampler", "euler_ancestral"))
                learned_params["scheduler"].append(gen_data.get("scheduler", "karras"))
                break

    # 学習結果を整理
    if learned_models:
        # 使用回数が多い順にソート
        sorted_models = sorted(learned_models.items(), key=lambda x: x[1], reverse=True)
        learned["models"] = [model for model, count in sorted_models]

    if learned_loras:
        # 使用回数が多い順にソート
        sorted_loras = sorted(learned_loras.items(), key=lambda x: x[1], reverse=True)
        learned["loras"] = [lora for lora, count in sorted_loras]

    # パラメータの平均値または最頻値を計算
    if learned_params["steps"]:
        learned["params"]["steps"] = max(set(learned_params["steps"]), key=learned_params["steps"].count)
    if learned_params["guidance_scale"]:
        learned["params"]["guidance_scale"] = sum(learned_params["guidance_scale"]) / len(learned_params["guidance_scale"])
    if learned_params["width"]:
        learned["params"]["width"] = max(set(learned_params["width"]), key=learned_params["width"].count)
    if learned_params["height"]:
        learned["params"]["height"] = max(set(learned_params["height"]), key=learned_params["height"].count)
    if learned_params["sampler"]:
        learned["params"]["sampler"] = max(set(learned_params["sampler"]), key=learned_params["sampler"].count)
    if learned_params["scheduler"]:
        learned["params"]["scheduler"] = max(set(learned_params["scheduler"]), key=learned_params["scheduler"].count)

    print(f"📊 学習結果: {matched_count}/{len(high_score_images)}件の高評価画像を分析")
    if learned["models"]:
        print(f"   学習されたモデル: {len(learned['models'])}件（上位: {learned['models'][:3]}）")
    if learned["loras"]:
        print(f"   学習されたLoRA: {len(learned['loras'])}件（上位: {learned['loras'][:3]}）")

    return learned


def wait_for_output_filenames(prompt_id: str, timeout: int = 300) -> Optional[List[str]]:
    """
    ComfyUIの履歴APIから実際の出力ファイル名を取得

    Args:
        prompt_id: プロンプトID
        timeout: タイムアウト（秒）

    Returns:
        出力ファイル名のリスト
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    outputs = prompt_data.get("outputs", {})
                    output_filenames = []
                    for node_id, node_output in outputs.items():
                        images = node_output.get("images", [])
                        for img in images:
                            filename = img.get("filename", "")
                            subfolder = img.get("subfolder", "")
                            if filename:
                                if subfolder:
                                    output_filenames.append(f"{subfolder}/{filename}")
                                else:
                                    output_filenames.append(filename)
                    if output_filenames:
                        return output_filenames
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return None


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


# コマンドライン引数で生成数を指定
parser = argparse.ArgumentParser(description="マナごのみ画像生成")
parser.add_argument("-n", "--num", type=int, default=50, help="生成する画像数（デフォルト: 50）")
# 「ムフフ＝セクシー寄り」(※露骨な性行為/性器描写は含めない) のプリセット
parser.add_argument(
    "--mode",
    choices=["safe", "mufufu"],
    default="safe",
    help="プロンプトプリセット（safe:通常/非露骨, mufufu:セクシー寄り/非露骨）",
)
args = parser.parse_args()
num_images = args.num
mode = args.mode

# 学習された好みを取得
print("=" * 60)
print("マナごのみ画像生成（評価・学習機能統合版）")
print("=" * 60)
print()
learned_preferences = learn_from_evaluations()
print()

MUFUFU_NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, "
    "username, blurry, bad feet, multiple people, multiple persons, "
    "bad proportions, bad body structure, deformed body, malformed limbs, incorrect anatomy, "
    "wrong anatomy, broken anatomy, distorted anatomy, "
    "bad hands, missing fingers, extra fingers, fused fingers, "
    "too many fingers, fewer digits, missing digits, "
    "bad feet, malformed feet, extra feet, missing feet, "
    "bad arms, malformed arms, extra arms, missing arms, "
    "bad legs, malformed legs, extra legs, missing legs, "
    "disconnected limbs, floating limbs, bad joints, malformed joints"
    # 安全側：未成年/露骨な性表現の誘発を避ける
    ", child, loli, teen, underage, young, schoolgirl"
    ", nude, naked, nipples, areola, pussy, penis, testicles, sex, intercourse, blowjob, fellatio, anal"
)

# プロンプト要素（非露骨）
clothing_style = ["clear gyaru style", "pure gyaru style", "innocent gyaru style", "cute gyaru style"]
bodies = ["slim body", "toned body", "athletic body", "fit body"]
breast_size = ["medium breasts", "large breasts", "D cup"]
hair_styles = ["long hair", "medium hair", "wavy hair", "straight hair", "black hair"]
skin_tone = ["pale skin", "fair skin"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting"]

if mode == "mufufu":
    outfits = [
        "lingerie",
        "lace lingerie",
        "silk lingerie",
        "bodysuit",
        "bikini",
        "one-piece swimsuit",
        "short skirt",
        "crop top and shorts",
    ]
    poses = ["lying on bed", "sitting on bed", "standing", "kneeling", "leaning"]
    expressions = ["seductive", "confident", "playful", "smile"]
    scenes = ["boudoir", "bedroom", "hotel room", "studio portrait"]
    extra_tags = ["adult woman", "20s", "makeup", "glossy lips", "cleavage", "stockings", "high heels"]
else:
    outfits = [
        "street fashion",
        "casual outfit",
        "chic dress",
        "jacket and skirt",
        "crop top and shorts",
    ]
    poses = ["sitting", "standing", "kneeling", "walking", "leaning"]
    expressions = ["smile", "happy", "confident", "innocent", "playful"]
    scenes = ["city street", "cafe", "studio portrait", "hotel room", "bedroom (clothed)"]
    extra_tags = ["adult woman", "20s"]

print(f"利用可能なモデル: {len(available_models)}件")
print(f"利用可能なLoRA: {len(available_loras)}件")
print(f"生成数: {num_images}枚")
print()

prompt_ids = []
success_count = 0
failed_count = 0
used_models = []  # 使用したモデルを記録（多様性を確保）

print(f"🎨 {num_images}枚の画像を生成します...")
print()

# 生成メタデータを保存するための辞書
generation_metadata = {}

for i in range(num_images):
    print(f"[{i+1}/{num_images}] 生成中...", end=" ", flush=True)

    # モデル選択（50%の確率で学習されたモデルを使用）
    if learned_preferences.get("models") and random.random() < 0.5:
        # 学習されたモデルから選択（利用可能なもののみ）
        learned_models_available = [m for m in learned_preferences["models"] if m in available_models]
        if learned_models_available:
            model = random.choice(learned_models_available)
        else:
            model = random.choice(available_models)
    else:
        model = random.choice(available_models)

    # 同じモデルを連続で使わないようにする（多様性確保）
    if used_models and len(used_models) >= 3:
        recent_models = used_models[-3:]
        if model in recent_models:
            # 別のモデルを選択
            other_models = [m for m in available_models if m not in recent_models]
            if other_models:
                model = random.choice(other_models)
    used_models.append(model)
    if len(used_models) > 10:
        used_models.pop(0)

    # LoRA選択（60%の確率で学習されたLoRAを使用）
    num_loras = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
    loras = []
    if available_loras and num_loras > 0:
        if learned_preferences.get("loras") and random.random() < 0.6:
            # 学習されたLoRAから選択（利用可能なもののみ）
            learned_loras_available = [l for l in learned_preferences["loras"] if l in available_loras]
            if learned_loras_available:
                selected_loras = random.sample(
                    learned_loras_available,
                    min(num_loras, len(learned_loras_available))
                )
            else:
                selected_loras = random.sample(available_loras, min(num_loras, len(available_loras)))
        else:
            selected_loras = random.sample(available_loras, min(num_loras, len(available_loras)))

        for lora_name in selected_loras:
            lora_strength = round(random.uniform(0.5, 0.8), 2)
            loras.append((lora_name, lora_strength))

    # プロンプト生成（露骨な性行為/性器の描写は避ける）
    prompt_parts = [
        "Japanese",
        "Japanese woman",
        "1girl",
        "solo",
        random.choice(clothing_style),
        random.choice(outfits),
        random.choice(poses),
        random.choice(expressions),
        random.choice(bodies),
        random.choice(breast_size),
        random.choice(skin_tone),
        *extra_tags,
        "perfect proportions",
        "correct anatomy",
        "beautiful",
        "gorgeous",
        "stunning",
        random.choice(scenes),
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

    # パラメータ設定（学習されたパラメータを参考に）
    if is_sdxl_model(model) or is_sd3_model(model):
        if learned_preferences.get("params", {}).get("steps"):
            steps = learned_preferences["params"]["steps"]
        else:
            steps = random.choice([50, 55, 60, 65])

        if learned_preferences.get("params", {}).get("width") and learned_preferences.get("params", {}).get("height"):
            width = learned_preferences["params"]["width"]
            height = learned_preferences["params"]["height"]
        else:
            width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        if learned_preferences.get("params", {}).get("steps"):
            steps = learned_preferences["params"]["steps"]
        else:
            steps = random.choice([60, 65, 70, 75])

        if learned_preferences.get("params", {}).get("width") and learned_preferences.get("params", {}).get("height"):
            width = learned_preferences["params"]["width"]
            height = learned_preferences["params"]["height"]
        else:
            width, height = random.choice([(768, 1024), (1024, 768), (896, 1152), (1024, 1024)])

    if learned_preferences.get("params", {}).get("guidance_scale"):
        guidance_scale = round(learned_preferences["params"]["guidance_scale"], 1)
    else:
        guidance_scale = round(random.uniform(8.0, 9.5), 1)

    if learned_preferences.get("params", {}).get("sampler"):
        sampler = learned_preferences["params"]["sampler"]
    else:
        sampler = random.choice(["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"])

    if learned_preferences.get("params", {}).get("scheduler"):
        scheduler = learned_preferences["params"]["scheduler"]
    else:
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

    print(f"{model[:35]}{lora_info}")
    print(f"  {width}x{height}, {steps}steps, CFG:{guidance_scale}, Seed:{seed}")

    try:
        payload = {"prompt": workflow}
        response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            if prompt_id:
                prompt_ids.append(prompt_id)
                success_count += 1
                print(f"  [OK] {prompt_id}")

                # 実際の出力ファイル名を取得
                output_filenames = wait_for_output_filenames(prompt_id)

                # 生成メタデータを保存
                gen_metadata = {
                    "model": model,
                    "loras": [{"name": l[0], "strength": l[1]} for l in loras] if loras else [],
                    "prompt": prompt,
                    "negative_prompt": MUFUFU_NEGATIVE_PROMPT,
                    "steps": steps,
                    "guidance_scale": guidance_scale,
                    "width": width,
                    "height": height,
                    "sampler": sampler,
                    "scheduler": scheduler,
                    "seed": seed,
                    "prompt_id": prompt_id,
                    "output_filenames": output_filenames if output_filenames else [],
                    "output_paths": [str(OUTPUT_DIR / fname) for fname in (output_filenames or [])],
                }
                generation_metadata[prompt_id] = gen_metadata
            else:
                failed_count += 1
                print("  [ERROR] プロンプトIDが取得できませんでした")
        else:
            failed_count += 1
            print(f"  [ERROR] HTTP {response.status_code}")
    except Exception as e:
        failed_count += 1
        print(f"  [ERROR] {e}")

    print()
    time.sleep(1)  # レート制限対策

# 生成メタデータを保存
if generation_metadata:
    # 既存のメタデータを読み込んでマージ
    existing_metadata = {}
    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
        except Exception as e:
            print(f"⚠️ 既存メタデータの読み込みエラー: {e}")

    existing_metadata.update(generation_metadata)

    # 保存
    GENERATION_METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(GENERATION_METADATA_DB, 'w', encoding='utf-8') as f:
            json.dump(existing_metadata, f, ensure_ascii=False, indent=2)
        print(f"✅ 生成メタデータを保存しました: {len(generation_metadata)}件")
    except Exception as e:
        print(f"⚠️ 生成メタデータの保存エラー: {e}")

print("=" * 60)
print(f"生成リクエスト完了: 成功 {success_count}件 / 失敗 {failed_count}件")
print("=" * 60)
print("画像はComfyUIの出力フォルダに保存されます。")
print("評価UIで評価すると、次回の生成に反映されます。")
