#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カスタムプロンプトを使用した画像生成スクリプト
ユーザーが提供したプロンプトを解析して使用
"""

import requests
import json
import time
import sys
import io
import random
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from _paths import COMFYUI_PORT

COMFYUI_URL = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
OUTPUT_DIR = Path("C:/ComfyUI/output")
GENERATION_METADATA_DB = Path("C:/ComfyUI/input/mana_favorites/generation_metadata.json")

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

# LoRA検出
if COMFYUI_LORA_DIR.exists():
    for lora_file in COMFYUI_LORA_DIR.glob("*.safetensors"):
        lora_name = lora_file.name
        if not any(kw in lora_name.lower() for kw in ["qwen", "llm", "text"]):
            available_loras.append(lora_name)

# ユーザーが提供したプロンプトテンプレート
CUSTOM_PROMPTS = [
    {
        "positive": "(8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.4), (extremely detailed CG unity 8k wallpaper), 1 girl, (nsfw), (lying on bed:1.4), long hair, cleavage, (perfect_pussy:1.4), (small breasts:1.2), spread legs, (shiny silk stockings:1.2), beautiful face",
        "negative": "easynegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), low res, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans, extra fingers, fewer fingers, strange fingers, bad hand, mole, ((extra legs)), ((extra hands)), bad-hands-5, hands",
        "loras": [("GodPussy1 v2", 0.5)],
        "steps": 127,
        "cfg_scale": 7,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "width": 768,
        "height": 1152,
        "model": "braBeautifulRealistic_brav5"
    },
    {
        "positive": "(RAW photo:1.2),(photorealistic:1.4),(masterpiece:1.3),(best quality:1.4),ultra high res, HDR,8k resolution, dreamlike, check commentary, commentary request, scenery,((no text)), 1girl, (cleavage:1.5), (large breasts:1.5), (pubic hair:1.5),(lifting shirt), (detailed laced underpants:1.4), (full body), (looking down:1.5), (close up), look at the viewer, naughty face, (touching self hair:1.3), (tattoo:1.3), topless, arm, (close up:1.5), (focus on breasts), (detailed eyes),(detailed facial features), (detailed clothes features), (breast blush) trending on cg society, plasticine, bob hair, (strong and toned abs), ((beautiful woman)), wearing choker, thigh choker, very pale white skin, in snow, feminine and muscular, smiling, wet skin, female focus",
        "negative": "EasyNegative,bad_prompt,ng_deepnegative_v1_75t,(worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6), manboobs, backlight,(ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, glans",
        "loras": [("virtualgirlRin_v30", 0.3), ("upshirtUnderboob_v10", 1.35)],
        "steps": 25,
        "cfg_scale": 8,
        "sampler": "dpmpp_sde",
        "scheduler": "karras",
        "width": 512,
        "height": 1024,
        "model": "chilloutmix_NiPrunedFp32Fix"
    },
    {
        "positive": "nsfw, (A girl in reversecow position has sex with a boy:1.3), best quality, masterpiece, ultra detailed, (realistic, photo realistic:1.37), very detailed faces, an extremely delicate and beautiful, extremely detailed, (light on face:1.2), 1boy, 1girl, filmg, black_hair, breasts, clitoris, hairless_puccy, girl_on_top, japanese_ldol, hetero, lips, makeup, (female_orgasm:1.4), (open_mouth), (looking at viewer:1.2), long_hair, small_breasts, (skinny), navel, nipples, uncensored, (revcowgirl:1.4), (hairless_puccy:1.2), (huge_penis penetrating pussy), cum_in_puccy, realistic, sex, sex_from_behind, straddling, testicles, vaginal, cumdrip, pale skin, in room, dark_background, (blurry background, bokeh)",
        "negative": "(pube, pubic_hair:1.8), (panties:2), (Underwear:2), (skirt:2), (shorts:2), (pants:2), (swimsuit:2), (bikini:2), (thong,:2), (Denim_skirt:2), (Denim_shorts:2), (Denim_jeans:2), bad-picture-chill-75v, badhandv4",
        "loras": [("FilmG3", 0.7), ("cowgirl-1.0", 0.5)],
        "steps": 40,
        "cfg_scale": 8.5,
        "sampler": "dpmpp_2m_alt",
        "scheduler": "karras",
        "width": 512,
        "height": 786,
        "model": "majicmixRealistic_v4"
    },
    {
        "positive": "score_9, score_8_up, score_7_up, 1girl, 18 years old, shining skin, perfect quality, high quality, ambient occlusion, raytracing, source_anime, shining glossy skin, soft lighting, realistic skin, blum effect, pale skin, masterpiece, absolutely eye-catching, (((close shot of tits:1.3, tits focused:1.2))), perky nipples, perfect round breast, large breasrs, sweaty, (detailed sweat drops:1.3), (goosebumps:1.1), solo, excessive sweat:1.2, ((underboob, from below)), slim waist, (slender body), soft abs, face out of frame",
        "negative": "score_6, score_5, score_4, skinny, anorexic, furry, (loli, child), muscular body, small breast, low detailed face, asian, bad face, ugly face, mutated hands, negative_hand, (polydactyly:1.2), (polydactyl:1.2), bad fingers, (milf:1.3), face paint, ugly nose, bad nose, glowing eyes, signature, watermark, comics, frames, full body, face focused, face, head, full head, lips, mouth, nose, belly",
        "loras": [],
        "steps": 8,
        "cfg_scale": 1,
        "sampler": "euler",
        "scheduler": "normal",
        "width": 832,
        "height": 1216,
        "model": ""
    },
    {
        "positive": "(RAW photo, best quality), (realistic, photo-realistic:1.3), best quality ,masterpiece, an extremely delicate and beautiful, extremely detailed ,CG ,unity ,2k wallpaper, Amazing, finely detail, masterpiece, light smile, best quality, extremely detailed CG unity 8k wallpaper, huge filesize , ultra-detailed, highres, extremely detailed, 1girl, maid,(nude:1.2),(moist pussy:1), (spread legs), hair ornament, looking at looking at viewer, small breasts",
        "negative": "bra, covered nipples, underwear,EasyNegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans,extra fingers,fewer fingers,((watermark:2)),(white letters:1), (multi nipples), lowres, bad anatomy, bad hands, text, error, missing fingers,extra digit, fewer digits, cropped, worst quality, low qualitynormal quality, jpeg artifacts, signature, watermark, username,bad feet, {Multiple people},lowres,bad anatomy,bad hands, text, error, missing fingers,extra digit, fewer digits, cropped, worstquality, low quality, normal quality,jpegartifacts,signature, watermark, blurry,bad feet,cropped,poorly drawn hands,poorly drawn face,mutation,deformed,worst quality,low quality,normal quality,jpeg artifacts,signature,extra fingers,fewer digits,extra limbs,extra arms,extra legs,malformed limbs,fused fingers,too many fingers,long neck,cross-eyed,mutated hands,polar lowres,bad body,bad proportions,gross proportions,text,error,missing fingers,missing arms,extra arms,missing legs,wrong feet bottom render,extra digit,abdominal stretch, glans, pants, briefs, knickers, kecks, thong, {{fused fingers}}, {{bad body}}, ((long hair))",
        "loras": [("japaneseDollLikeness_v10", 0.2), ("koreanDollLikeness_v15", 0.2), ("cuteGirlMix4_v10", 0.4), ("chilloutmixss30_v30", 0.2), ("pureerosface_v1", 0.8)],
        "steps": 20,
        "cfg_scale": 8,
        "sampler": "dpmpp_sde",
        "scheduler": "karras",
        "width": 512,
        "height": 768,
        "model": "chilloutmix_NiPrunedFp32Fix"
    },
    {
        "positive": "masterpiece, best quality, ultra detailed, 8k, realistic, photo-realistic, 1girl, beautiful, detailed",
        "negative": "worst quality, low quality, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet",
        "loras": [("mix4", 1.0), ("Addams", 1.0), ("breastinClass", 1.0), ("zyd232sChineseGirl_v16", 1.0), ("badhandv4", 1.0), ("GoodHands-beta2", 1.0), ("GoodHands-vanilla", 1.0), ("bad-picture-chill-75v", 1.0), ("ng_deepnegative_v1_75t", 1.0)],
        "steps": 150,
        "cfg_scale": 7.5,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "width": 512,
        "height": 768,
        "model": "majicmixRealistic_v7"
    },
    {
        "positive": "(RAW photo:1.2), (photorealistic:1.4),(masterpiece:1.4),(best quality:1.4),ultra high res,((detailed facial features)),HDR,8k resolution,Kpop idol,aegyo sal,1boy, 1girl, animal ears, bangs, blush, bodysuit, breasts, censored, covered navel, fake animal ears, grey hair, gun, headphones, headset, hetero, jacket, large breasts, latex bodysuit, long hair, looking at viewer, mosaic censoring, open mouth, penis, pink bodysuit, pink eyes, pussy, rifle, sex, simple background, skin tight, solo focus, spread legs, twintails, vaginal, weapon,alice (nikke),(masterpiece:1.4),(best quality:1.4),(shiny skin),(slime girl)",
        "negative": "paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6), manboobs, backlight,(ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, NG_DeepNegative_V1_75T,pubic hair, glans,nsfw",
        "loras": [("koreanDollLikeness_v10", 0.2), ("aliceNikke_v20", 1.0)],
        "steps": 20,
        "cfg_scale": 7,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "width": 512,
        "height": 768,
        "model": ""
    },
    {
        "positive": "(RAW photo:1.2), (photorealistic:1.4),(masterpiece:1.4),(best quality:1.4),ultra high res,((detailed facial features)),HDR,8k resolution,Kpop idol,aegyo sal,1boy, 1girl, animal ears, anus, ass, ass grab, blush, bodysuit, breasts, uncensored, cropped jacket, from behind, gloves, grey hair, headphones, hetero, jacket, large breasts, latex, latex bodysuit, long hair, long sleeves, looking at viewer, looking back, open mouth, penis, pink bodysuit, pink eyes, pink gloves, pov, pussy, sex, skin tight, solo focus, spread pussy, twintails, vaginal,alice (nikke),(masterpiece:1.4),(best quality:1.4),(shiny skin),interior",
        "negative": "paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6), manboobs, backlight,(ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, NG_DeepNegative_V1_75T,pubic hair, glans,nsfw",
        "loras": [("koreanDollLikeness_v10", 0.2), ("aliceNikke_v20", 1.0)],
        "steps": 20,
        "cfg_scale": 7,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "width": 512,
        "height": 768,
        "model": ""
    },
    {
        "positive": "mix4,(8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37),1girl,cute,cityscape, night, rain, wet,professional lighting, photon mapping, radiosity, physically-based rendering, full body,thighhighs,legs together, breasts, peeing",
        "negative": "paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans",
        "loras": [("cuteGirlMix4_v10", 1.0)],
        "steps": 20,
        "cfg_scale": 6.5,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "width": 512,
        "height": 840,
        "model": "chilloutmix_NiPrunedFp32Fix"
    }
]


def parse_lora_from_prompt(prompt: str) -> List[Tuple[str, float]]:
    """プロンプトからLoRA情報を抽出"""
    loras = []
    # <lora:Name:weight> 形式を検索
    pattern = r'<lora:([^:>]+):([0-9.]+)>'
    matches = re.findall(pattern, prompt, re.IGNORECASE)
    for name, weight in matches:
        loras.append((name.strip(), float(weight)))
    return loras


def find_lora_file(lora_name: str) -> Optional[str]:
    """LoRA名から実際のファイル名を検索"""
    # マッピングテーブル（類似ファイル名）
    lora_mapping = {
        "cuteGirlMix4_v10": "Cute_girl_mix4_14171",
        "pureerosface_v1": "Pure Eros Face_4514",
        "pureerosface_v1:0.8": "Pure Eros Face_4514",
    }

    # マッピングテーブルをチェック
    if lora_name in lora_mapping:
        mapped_name = lora_mapping[lora_name]
        for lora_file in available_loras:
            if mapped_name.lower() in lora_file.lower():
                return lora_file

    # 部分一致で検索（より柔軟に）
    lora_name_lower = lora_name.lower().replace("_", "").replace("-", "").replace(" ", "")
    for lora_file in available_loras:
        lora_file_lower = lora_file.lower().replace("_", "").replace("-", "").replace(" ", "")
        # キーワード抽出
        keywords = [kw for kw in lora_name_lower.split() if len(kw) > 3]
        if keywords:
            # 主要キーワードが含まれているかチェック
            if any(kw in lora_file_lower for kw in keywords):
                return lora_file
        # 元の方法も試す
        if lora_name.lower() in lora_file.lower() or lora_file.lower() in lora_name.lower():
            return lora_file
    return None


def create_workflow_with_loras(
    prompt: str,
    negative_prompt: str,
    model: str,
    loras: List[Tuple[str, float]] = None,
    steps: int = 50,
    guidance_scale: float = 7.5,
    width: int = 768,
    height: int = 1024,
    sampler: str = "euler_ancestral",
    scheduler: str = "karras",
    seed: int = -1
):
    """LoRA対応のワークフロー作成"""
    workflow = {
        "1": {"inputs": {"ckpt_name": model}, "class_type": "CheckpointLoaderSimple"},
    }

    current_model = ["1", 0]
    current_clip = ["1", 1]
    node_id = 8

    # LoRAを適用
    if loras:
        for lora_name, lora_strength in loras:
            lora_file = find_lora_file(lora_name)
            if lora_file:
                workflow[str(node_id)] = {
                    "inputs": {
                        "lora_name": lora_file,
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
            else:
                print(f"  ⚠️ LoRAが見つかりません: {lora_name}")

    # テキストエンコーダー
    workflow["2"] = {"inputs": {"text": prompt, "clip": current_clip}, "class_type": "CLIPTextEncode"}
    workflow["3"] = {"inputs": {"text": negative_prompt, "clip": current_clip}, "class_type": "CLIPTextEncode"}

    # サンプラー
    workflow["4"] = {
        "inputs": {
            "seed": seed if seed >= 0 else random.randint(1, 2**32 - 1),
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


def wait_for_output_filenames(prompt_id: str, timeout: int = 300) -> Optional[List[str]]:
    """ComfyUIの履歴APIから実際の出力ファイル名を取得"""
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


# コマンドライン引数
parser = argparse.ArgumentParser(description='カスタムプロンプトで画像生成')
parser.add_argument('-n', '--num', type=int, default=10, help='生成する画像数（デフォルト: 10）')
parser.add_argument('-t', '--template', type=int, choices=[0, 1, 2, 3, 4, 5, 6, 7, 8], help='使用するプロンプトテンプレート（0-8）')
args = parser.parse_args()
num_images = args.num

print("=" * 60)
print("カスタムプロンプト画像生成")
print("=" * 60)
print()
print(f"利用可能なモデル: {len(available_models)}件")
print(f"利用可能なLoRA: {len(available_loras)}件")
print(f"生成数: {num_images}枚")
print()

prompt_ids = []
success_count = 0
failed_count = 0
generation_metadata = {}

for i in range(num_images):
    print(f"[{i+1}/{num_images}] 生成中...", end=" ", flush=True)

    # プロンプトテンプレートを選択
    if args.template is not None:
        template = CUSTOM_PROMPTS[args.template]
    else:
        template = random.choice(CUSTOM_PROMPTS)

    # モデルを確認・選択
    model = template.get("model", "")
    if model not in available_models:
        # モデルが見つからない場合、利用可能なモデルから選択
        model = random.choice(available_models)
        print(f"  ⚠️ 指定モデル '{template.get('model')}' が見つかりません。'{model}' を使用します")

    # プロンプトからLoRA情報を抽出
    prompt = template["positive"]
    loras = template.get("loras", [])

    # プロンプト内のLoRA記法を削除
    prompt = re.sub(r'<lora:[^>]+>', '', prompt, flags=re.IGNORECASE)

    # LoRAファイルを検索
    valid_loras = []
    for lora_name, lora_strength in loras:
        lora_file = find_lora_file(lora_name)
        if lora_file:
            valid_loras.append((lora_file, lora_strength))
        else:
            print(f"  ⚠️ LoRA '{lora_name}' が見つかりません")

    # パラメータ
    steps = template.get("steps", 50)
    cfg_scale = template.get("cfg_scale", 7.5)
    width = template.get("width", 768)
    height = template.get("height", 1024)
    sampler = template.get("sampler", "euler_ancestral")
    scheduler = template.get("scheduler", "karras")
    seed = random.randint(1, 2**32 - 1)

    workflow = create_workflow_with_loras(
        prompt=prompt,
        negative_prompt=template["negative"],
        model=model,
        loras=valid_loras if valid_loras else None,
        steps=steps,
        guidance_scale=cfg_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed,
    )

    lora_info = ""
    if valid_loras:
        lora_names = [l[0][:20] for l in valid_loras]
        lora_info = f" + LoRA:{'+'.join(lora_names)}"

    print(f"{model[:35]}{lora_info}")
    print(f"  {width}x{height}, {steps}steps, CFG:{cfg_scale}, Seed:{seed}")

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
                    "loras": [{"name": l[0], "strength": l[1]} for l in valid_loras] if valid_loras else [],
                    "prompt": prompt,
                    "negative_prompt": template["negative"],
                    "steps": steps,
                    "guidance_scale": cfg_scale,
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
    time.sleep(1)

# 生成メタデータを保存
if generation_metadata:
    existing_metadata = {}
    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
        except Exception:
            pass

    existing_metadata.update(generation_metadata)

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
