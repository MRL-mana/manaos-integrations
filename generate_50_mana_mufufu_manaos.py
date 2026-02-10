#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マナごのみ画像生成スクリプト（評価・学習機能統合版）
"""

import os
import re
import requests
import json
import time
import sys
import io
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from PIL import Image, ImageOps

if sys.platform == "win32":
    # PowerShellのパイプ等でstdoutが壊れないようにガード
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
COMFYUI_POST_TIMEOUT = int(os.getenv("COMFYUI_POST_TIMEOUT", "90"))
COMFYUI_MAX_RETRIES = int(os.getenv("COMFYUI_MAX_RETRIES", "2"))
COMFYUI_BASE = Path(os.getenv("COMFYUI_BASE", "C:/ComfyUI"))
EVALUATION_DB = COMFYUI_BASE / "input/mana_favorites/evaluation.json"
GENERATION_METADATA_DB = COMFYUI_BASE / "input/mana_favorites/generation_metadata.json"
OUTPUT_DIR = COMFYUI_BASE / "output"

# サムネ（A相当: 新規生成分は生成直後に作っておく）
THUMBS_DIRNAME = os.getenv("MANAOS_THUMBS_DIRNAME", ".thumbs").strip() or ".thumbs"
THUMB_SIZE = int(os.getenv("MANAOS_THUMB_SIZE", "512"))
THUMB_QUALITY = int(os.getenv("MANAOS_THUMB_QUALITY", "82"))

# プロンプト品質・ネガティブの一元化
try:
    from mufufu_config import (
        MUFUFU_NEGATIVE_PROMPT as CONFIG_NEGATIVE,
        ANATOMY_POSITIVE_TAGS,
        QUALITY_TAGS,
        build_ordered_prompt,
        get_default_negative_prompt_safe,
        RECOMMENDED_MODEL_LORA_PAIRS,
    )
except ImportError:
    CONFIG_NEGATIVE = None
    ANATOMY_POSITIVE_TAGS = ""
    QUALITY_TAGS = "masterpiece, best quality, ultra detailed, 8k"
    build_ordered_prompt = None
    get_default_negative_prompt_safe = lambda: ""
    RECOMMENDED_MODEL_LORA_PAIRS = {}

# モデルとLoRAの検出（環境変数で上書き可）
COMFYUI_MODELS_DIR = Path(os.getenv("COMFYUI_MODELS", str(COMFYUI_BASE / "models/checkpoints")))
COMFYUI_LORA_DIR = Path(os.getenv("COMFYUI_LORAS", str(COMFYUI_BASE / "models/loras")))

available_models = []
# モデル検出（全件）
all_models = []
for model_file in COMFYUI_MODELS_DIR.glob("*.safetensors"):
    all_models.append(model_file.name)
for model_file in COMFYUI_MODELS_DIR.glob("*.ckpt"):
    all_models.append(model_file.name)
all_models = [m for m in all_models if "\\" not in m and "/" not in m]

# LoRA検出（全件・キーワード除外は後で profile に応じて適用）
all_loras = []
if COMFYUI_LORA_DIR.exists():
    for lora_file in list(COMFYUI_LORA_DIR.glob("*.safetensors")) + list(
        COMFYUI_LORA_DIR.glob("*.pt")
    ):
        all_loras.append(lora_file.name)

# 露骨系LoRAを除外するキーワード（profile=safe のときのみ適用）
excluded_lora_keywords = [
    "qwen",
    "llm",
    "text",
    "nsfw",
    "nude",
    "nudity",
    "sex",
    "intercourse",
    "porn",
    "bdsm",
    "dildo",
    "masturb",
    "penis",
    "pussy",
    "cum",
    "public indecency",
    "rape",
    "incest",
]
# DiT/SD3/Flux/LTX/Qwen用LoRA（SD1.5/SDXLと互換性なし）。lab含め常に除外
# diffusion_model.layers / adaLN_modulation は DiT 系。これらを含むLoRAはキーが合わず "lora key not loaded" になる
excluded_lora_architecture_keywords = [
    "flux",
    "sd3",
    "sdx3",
    "ltx",
    "ltx2",
    "dit",
    "wan2",
    "wan2.2",
    "qwen",
    "lightning_2step",  # 2step 系の一部が DiT 形式で lora key not loaded になるため除外
    "lightning",        # diffusion_model.layers 系の LoRA を除外（DiT 形式）
]

# 問題モデルリスト（露骨系・動画用・読み込み不可等）。profile=lab のときは使用可
problematic_models = [
    "0482 dildo masturbation_v1_pony.safetensors",
    "0687 public indecency_v1_pony.safetensors",
    "ltx-2-19b-distilled.safetensors",
    "qqq-BDSM-v3-000010.safetensors",
    "ZIT_Amateur_Nudes_V2.safetensors",
    "wan2.2_t2v_highnoise_masturbation_v1.0.safetensors",
    "waiIllustriousSDXL_v160.safetensors",
    "lazypos.safetensors",
    "shibari_v20.safetensors",
    "Character_Mix_FarrahMixerV2_ZIT.safetensors",
    "ZiTD3tailed4nime.safetensors",
    "IC-V7 E10.safetensors",
]
# 常に除外するモデル（safe/lab どちらでも使わない）
# 不安定になる主な理由:
#  - Could not detect model type: 形式・メタデータが SD1.5/SDXL と異なる
#  - 出力待ちでハング: ニッチなPony/特化モデルは読み込み・推論が極端に遅い、またはキューで詰まる
#  - 動画/DiT用チェックポイントが checkpoints に混ざっている
unusable_models = [
    "OnOff.safetensors",
    "0687 public indecency_v1_pony.safetensors",
    "0482 dildo masturbation_v1_pony.safetensors",
    "lazypos.safetensors",
]
# 大文字小文字を区別せず除外するため（LazyPos.safetensors 等にも対応）
unusable_models_lower = {m.lower() for m in unusable_models}
# lab用: アダルト向けとして優先したいモデル（ファイル名に含まれるキーワード・小文字で照合）
LAB_PREFERRED_MODEL_KEYWORDS = (
    "pony",
    "nude",
    "nudes",
    "bdsm",
    "amateur",
    "illustrious",
    "shibari",
    "farrah",
    "dildo",
    "public indecency",
    "uncensored",
)
# lab用: アダルト系LoRAとみなすキーワード（これらを含むLoRAを優先して選ぶ）
LAB_PREFERRED_LORA_KEYWORDS = (
    "nsfw",
    "nude",
    "nudity",
    "sex",
    "uncensored",
    "adult",
    "ero",
    "pussy",
    "naked",
    "explicit",
)
# デフォルトは除外（parse_args 後に profile=lab なら all_models / all_loras を使う）
available_models = [
    m for m in all_models
    if m not in problematic_models and m.lower() not in unusable_models_lower
]
available_loras = [
    l
    for l in all_loras
    if not any(kw in l.lower() for kw in excluded_lora_keywords)
    and not any(kw in l.lower() for kw in excluded_lora_architecture_keywords)
]


def is_sdxl_model(model_name):
    return any(
        kw in model_name.lower()
        for kw in ["sdxl", "xl", "speciosa25d", "uwazumimix", "pony", "illustrious"]
    )


def is_sd3_model(model_name):
    return any(kw in model_name.lower() for kw in ["sd3", "flux"])


# SDXL用LoRAと判断するファイル名キーワード（shape mismatch を防ぐため SDXL モデルではこれらを含むLoRAのみ使用）
SDXL_LORA_INDICATORS = (
    "sdxl",
    "_xl",
    "xl_",
    "pony",
    "lux",
    "illustrious",
    "uwazumi",
    "speciosa",
)


def filter_loras_for_model(loras: List[str], model: str, use_all: bool = False) -> List[str]:
    """
    モデル種別に合うLoRAのみに絞る（SDXL用LoRAはSDXLモデルのみ、SD1.5用はSD1.5のみ）。
    SDXLモデルでは SDXL 用と判断できるLoRAのみ使用（lora_unet_* / shape invalid を防ぐ）。
    use_all=True のときは絞り込まない（全LoRAを候補にする）。
    """
    if use_all:
        return list(loras)
    sdxl = is_sdxl_model(model)
    sd3 = is_sd3_model(model)
    compatible = []
    for name in loras:
        lower = name.lower()
        has_sd15 = "sd15" in lower or "1.5" in lower or "sd 1.5" in lower
        has_sdxl_tag = any(ind in lower for ind in SDXL_LORA_INDICATORS)
        has_sdxl = (
            "sdxl" in lower or "_xl" in lower or "xl_" in lower or "pony" in lower or has_sdxl_tag
        )
        if sdxl:
            if has_sd15 and not has_sdxl:
                continue  # SD1.5専用LoRAはスキップ
            # SDXLモデルでは SDXL 用と分かるLoRAのみ使用（曖昧なLoRAはスキップして shape エラーを防ぐ）
            if not has_sdxl:
                continue
            compatible.append(name)
        elif sd3:
            compatible.append(name)
        else:
            if has_sdxl and not has_sd15:
                continue  # SDXL専用LoRAはSD1.5ではスキップ
            compatible.append(name)
    # SDXLで互換LoRAが無い場合は LoRA なしで生成（shape エラー防止）
    if sdxl and not compatible:
        return []
    return compatible if compatible else list(loras)


# コメントからマナの好みを判定するキーワード（学習の重み付けに使用）
_COMMENT_POSITIVE_KEYWORDS = (
    "良い",
    "いい",
    "最高",
    "気に入り",
    "きれい",
    "素晴らしい",
    "好み",
    "完璧",
    "かわいい",
    "美しい",
    "お気に入り",
    "good",
    "great",
    "love",
    "best",
)
_COMMENT_NEGATIVE_KEYWORDS = (
    "崩れ",
    "微妙",
    "悪い",
    "ダメ",
    "低い",
    "手が",
    "変",
    "違う",
    "いまいち",
    "bad",
    "worst",
    "崩れて",
    "崩壊",
    "残念",
)


def _comment_preference_weight(comment: str) -> float:
    """
    評価コメントから好みの重みを計算（1.0 = 通常、1.5 = 明確に良い、0.5 = 微妙）
    """
    if not comment or not isinstance(comment, str):
        return 1.0
    c = comment.strip()
    if not c:
        return 1.0
    # 英語は大文字小文字区別せず検索
    c_lower = c.lower()
    search_in = c + " " + c_lower
    has_positive = any(kw in search_in for kw in _COMMENT_POSITIVE_KEYWORDS)
    has_negative = any(kw in search_in for kw in _COMMENT_NEGATIVE_KEYWORDS)
    if has_negative and not has_positive:
        return 0.5  # ネガティブコメントあり → 重み半分（まだ参考にはする）
    if has_positive and not has_negative:
        return 1.5  # ポジティブコメントあり → マナの好みとして強く反映
    if has_positive and has_negative:
        return 1.0  # 両方 → ニュートラル
    return 1.0


def learn_from_evaluations() -> Dict:
    """
    評価データから好みを学習（スコア + コメントを反映）

    Returns:
        学習された好み（モデル、LoRA、パラメータ、コメント由来の傾向）
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
            "scheduler": [],
        },
        "comment_positive_count": 0,  # ポジティブコメント付き高評価数
        "comment_negative_count": 0,  # ネガティブコメント付き数
    }

    # 評価データと生成メタデータを読み込み
    evaluations = {}
    generation_metadata = {}

    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, "r", encoding="utf-8") as f:
                evaluations = json.load(f)
        except Exception as e:
            print(f"⚠️ 評価データの読み込みエラー: {e}")

    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                generation_metadata = json.load(f)
        except Exception as e:
            print(f"⚠️ 生成メタデータの読み込みエラー: {e}")

    if not evaluations or not generation_metadata:
        if not evaluations:
            print("  ※ 評価データがありません。評価UIで画像を評価すると学習に反映されます")
        elif not generation_metadata:
            print("  ※ 生成メタデータがありません。一括生成で画像を作成すると学習に反映されます")
        return learned

    # 高評価画像（スコア1-2）を特定し、コメント付きでリスト化
    high_score_images = []  # (img_path, eval_data)
    for img_path, eval_data in evaluations.items():
        score = eval_data.get("score", 0)
        if score <= 2:  # 高評価
            high_score_images.append((img_path, eval_data))

    if not high_score_images:
        return learned

    # 高評価画像に使用されたモデル、LoRA、パラメータを抽出（コメントで重み付け）
    matched_count = 0
    learned_models = {}
    learned_loras = {}
    learned_params = {
        "steps": [],
        "guidance_scale": [],
        "width": [],
        "height": [],
        "sampler": [],
        "scheduler": [],
    }

    for img_path, eval_data in high_score_images:
        img_name = Path(img_path).name
        img_path_str = str(img_path)
        comment = (eval_data.get("comment") or "").strip()
        weight = _comment_preference_weight(comment)
        if weight >= 1.3:
            learned["comment_positive_count"] += 1
        elif weight <= 0.6:
            learned["comment_negative_count"] += 1
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
                    if (
                        output_filename == img_name
                        or output_filename.endswith(img_name)
                        or img_name in output_filename
                    ):
                        matched = True

            # 4. output_pathをチェック（後方互換性）
            if not matched:
                output_path = gen_data.get("output_path", "")
                if output_path:
                    if str(output_path) == img_path_str or Path(output_path).name == img_name:
                        matched = True

            if matched:
                matched_count += 1
                # モデルを記録（コメントの好みで重み付け：ポジティブ→1.5倍、ネガティブ→0.5倍）
                model = gen_data.get("model", "")
                if model:
                    learned_models[model] = learned_models.get(model, 0) + weight

                # LoRAを記録（同様に重み付け）
                loras = gen_data.get("loras", [])
                for lora in loras:
                    lora_name = lora.get("name", "") if isinstance(lora, dict) else str(lora)
                    if lora_name:
                        learned_loras[lora_name] = learned_loras.get(lora_name, 0) + weight

                # パラメータを記録（重み付きサンプルとして扱うため従来どおり追加）
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
        learned["params"]["steps"] = max(
            set(learned_params["steps"]), key=learned_params["steps"].count
        )
    if learned_params["guidance_scale"]:
        learned["params"]["guidance_scale"] = sum(learned_params["guidance_scale"]) / len(
            learned_params["guidance_scale"]
        )
    if learned_params["width"]:
        learned["params"]["width"] = max(
            set(learned_params["width"]), key=learned_params["width"].count
        )
    if learned_params["height"]:
        learned["params"]["height"] = max(
            set(learned_params["height"]), key=learned_params["height"].count
        )
    if learned_params["sampler"]:
        learned["params"]["sampler"] = max(
            set(learned_params["sampler"]), key=learned_params["sampler"].count
        )
    if learned_params["scheduler"]:
        learned["params"]["scheduler"] = max(
            set(learned_params["scheduler"]), key=learned_params["scheduler"].count
        )

    print(f"📊 学習結果: {matched_count}/{len(high_score_images)}件の高評価画像を分析")
    if learned.get("comment_positive_count", 0) or learned.get("comment_negative_count", 0):
        print(
            f"   コメント反映: ポジティブ付き {learned.get('comment_positive_count', 0)}件 / "
            f"ネガティブ付き {learned.get('comment_negative_count', 0)}件（重み付けで学習）"
        )
    if learned["models"]:
        print(f"   学習されたモデル: {len(learned['models'])}件（上位: {learned['models'][:3]}）")
    if learned["loras"]:
        print(f"   学習されたLoRA: {len(learned['loras'])}件（上位: {learned['loras'][:3]}）")

    return learned


def wait_for_output_filenames(prompt_id: str, timeout: int = 450) -> Optional[List[str]]:
    """
    ComfyUIの履歴APIから実際の出力ファイル名を取得

    Args:
        prompt_id: プロンプトID
        timeout: タイムアウト（秒）

    Returns:
        出力ファイル名のリスト
    """
    start_time = time.time()
    last_log = 0
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
            elapsed = int(time.time() - start_time)
            if elapsed - last_log >= 30 and elapsed > 0:
                print(f"  ... 出力待ち {elapsed}秒", flush=True)
                last_log = elapsed
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    print(f"  [WARN] 出力待ちタイムアウト（{timeout}秒）", flush=True)
    return None


def _resolve_output_path(fname: str, profile: str) -> Path:
    """
    ComfyUIが返す filename は subfolder を含む場合がある (例: "lab/ComfyUI_x.png")。
    実ファイルの絶対パスに解決する。
    """
    s = str(fname or "").replace("\\", "/").lstrip("/")
    if "/" in s:
        return (OUTPUT_DIR / Path(s)).resolve()
    # subfolderが無い場合は profile に従う
    return ((OUTPUT_DIR / "lab" / s) if profile == "lab" else (OUTPUT_DIR / s)).resolve()


def _ensure_thumbnail(src: Path) -> Optional[Path]:
    """src のサムネを output/.thumbs 配下に作成して返す（既にあれば再利用）。"""
    try:
        src = src.resolve()
        if not src.exists() or not src.is_file():
            return None
        base = OUTPUT_DIR.resolve()
        try:
            rel = src.relative_to(base)
        except ValueError:
            return None

        thumbs_root = (base / THUMBS_DIRNAME).resolve()
        thumb_rel = rel.with_suffix(".jpg")
        thumb = (thumbs_root / thumb_rel).resolve()
        try:
            thumb.relative_to(thumbs_root)
        except ValueError:
            return None

        try:
            if thumb.exists() and thumb.stat().st_mtime >= src.stat().st_mtime:
                return thumb
        except Exception:
            pass

        thumb.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(str(src)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
            im.save(
                str(thumb),
                format="JPEG",
                quality=THUMB_QUALITY,
                optimize=True,
                progressive=True,
            )
        return thumb
    except Exception:
        return None


def _format_comfyui_error(err) -> str:
    """ComfyUI の error オブジェクトを読みやすい1行＋ヒントに整形する。"""
    if isinstance(err, dict):
        msg = err.get("message", err.get("details", str(err)))
        node_id = err.get("node_id")
        details = err.get("details")
        parts = [str(msg)]
        if node_id:
            parts.append(f" (node_id: {node_id})")
        if details and str(details) != str(msg):
            parts.append(f" | {details}")
        line = "".join(parts)
    else:
        line = str(err)
    # モデル/LoRA 未検出っぽいときは対処ヒントを付ける
    lower = line.lower()
    if (
        "checkpoint" in lower
        or "could not find" in lower
        or "lora" in lower
        or "not found" in lower
    ):
        line += (
            " → モデル/LoRA が ComfyUI の models フォルダに存在するか・ファイル名を確認してください"
        )
    return line


def _send_prompt_with_retry(payload: dict):
    """
    /prompt に POST し、一時的な失敗時のみリトライする。
    Returns: requests.Response or None（接続・タイムアウトで全リトライ失敗時）
    リトライ対象: 接続エラー、タイムアウト、HTTP 5xx。
    """
    last_exc = None
    for attempt in range(COMFYUI_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"{COMFYUI_URL}/prompt",
                json=payload,
                timeout=COMFYUI_POST_TIMEOUT,
            )
            # 5xx はリトライ
            if 500 <= resp.status_code < 600 and attempt < COMFYUI_MAX_RETRIES:
                time.sleep(3 * (attempt + 1))
                continue
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exc = e
            if attempt < COMFYUI_MAX_RETRIES:
                time.sleep(3 * (attempt + 1))
                continue
            raise last_exc
        except Exception:
            return None
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
    output_subfolder=None,
):
    """複数LoRA対応のワークフロー作成。output_subfolder 指定時は SaveImage の subfolder に保存（例: lab）"""
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
    workflow["2"] = {
        "inputs": {"text": prompt, "clip": current_clip},
        "class_type": "CLIPTextEncode",
    }
    workflow["3"] = {
        "inputs": {"text": negative_prompt, "clip": current_clip},
        "class_type": "CLIPTextEncode",
    }

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

    workflow["5"] = {
        "inputs": {"width": width, "height": height, "batch_size": 1},
        "class_type": "EmptyLatentImage",
    }
    workflow["6"] = {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"}
    save_inputs = {"filename_prefix": "ComfyUI", "images": ["6", 0]}
    if output_subfolder:
        save_inputs["subfolder"] = output_subfolder
    workflow["7"] = {"inputs": save_inputs, "class_type": "SaveImage"}
    return workflow


# 新規ダウンロード分（--prefer-new で優先して使うリスト）
NEW_MODELS = [
    "xxmix9realistic_v40.safetensors",
    "perfectdeliberate_v70.safetensors",
]
NEW_LORAS = [
    "GirlfriendMix2.safetensors",
    "EnvyPonyPrettyEyes01.safetensors",
    "XXMix9_v20LoRa.safetensors",
    "Illustration_E16.safetensors",
    "GirlfriendMix_v1_v20.safetensors",
]

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
parser.add_argument(
    "--prefer-new",
    action="store_true",
    help="新規ダウンロードしたモデル・LoRAを優先して使う",
)
parser.add_argument(
    "--no-wait",
    action="store_true",
    help="出力ファイル名を待たずに次へ（送信のみで完了。画像はComfyUIの出力フォルダに保存されます）",
)
parser.add_argument(
    "--profile",
    choices=["safe", "lab"],
    default=None,
    help="プロファイル（未指定時は MANAOS_IMAGE_DEFAULT_PROFILE または safe）",
)
parser.add_argument(
    "--use-all",
    action="store_true",
    help="全モデル・全LoRAを使う（問題リスト・キーワード除外・モデル種別フィルタを無効化）",
)
parser.add_argument(
    "--wait-timeout",
    type=int,
    default=450,
    metavar="SEC",
    help="出力ファイル名取得のタイムアウト秒（デフォルト: 450）",
)
parser.add_argument(
    "--prompt",
    type=str,
    default=None,
    help="固定プロンプト（指定時はこのテキストを使用。重み付きタグ (tag:1.2) はそのまま。※<lora:名:強度>は除去し、スクリプトのLoRA選択を使用）",
)
parser.add_argument(
    "--negative",
    type=str,
    default=None,
    help="固定ネガティブプロンプト（--prompt 使用時。未指定時はプロファイルのネガを使用）",
)
args = parser.parse_args()
num_images = args.num
mode = args.mode
prefer_new = getattr(args, "prefer_new", False)
no_wait = getattr(args, "no_wait", False)
# 未指定時: MANAOS_IMAGE_DEFAULT_PROFILE=lab なら lab、それ以外は safe
_profile_env = (os.getenv("MANAOS_IMAGE_DEFAULT_PROFILE") or "").strip().lower()
profile = args.profile if args.profile is not None else ("lab" if _profile_env == "lab" else "safe")
use_all = getattr(args, "use_all", False)
wait_timeout_sec = getattr(args, "wait_timeout", 450)
use_custom_prompt = bool(getattr(args, "prompt", None))
custom_prompt_raw = (getattr(args, "prompt", None) or "").strip()
custom_negative_raw = (getattr(args, "negative", None) or "").strip()


# DiT/SD3/Flux/LTX用LoRAはSD1.5/SDXLワークフローでは使わない（常に除外）
def _loras_for_sd_sdxl_workflow(loras_list):
    return [
        l
        for l in loras_list
        if not any(kw in l.lower() for kw in excluded_lora_architecture_keywords)
    ]


# --use-all: 全モデル・全LoRAを使う（問題リスト・キーワード除外・モデル種別フィルタを無効化）
if use_all:
    available_models = [m for m in all_models if m.lower() not in unusable_models_lower]
    available_loras = _loras_for_sd_sdxl_workflow(all_loras)
    print(
        "[USE-ALL] 問題リスト・キーワード除外・モデル種別フィルタを無効化しました（DiT/Flux/SD3/LTX用LoRAは除く）"
    )
    print("")
    print(
        "  ⚠️  警告: --use-all 使用時は互換性のないモデル/LoRAで ComfyUI がクラッシュする可能性があります。"
    )
    print("  ⚠️  問題が起きた場合は該当ファイルを models から一時退避してください。")
    print("")
# 闇の実験室（lab）: 除外していたモデル・LoRAも使用する
elif profile == "lab":
    available_models = [m for m in all_models if m.lower() not in unusable_models_lower]
    available_loras = _loras_for_sd_sdxl_workflow(all_loras)
    print("[LAB] 除外モデル・除外LoRAも使用します（露骨系含む。DiT/Flux/SD3/LTX用LoRAは除く）")
    print("")

# 学習された好みを取得
print("=" * 60)
print("マナごのみ画像生成（評価・学習機能統合版）")
print("=" * 60)
print()
learned_preferences = learn_from_evaluations()
print()

# ネガティブプロンプト: 身体崩れ対策＋品質＋安全（未成年・露骨表現の抑制）
if CONFIG_NEGATIVE:
    MUFUFU_NEGATIVE_PROMPT = CONFIG_NEGATIVE + ", " + get_default_negative_prompt_safe()
else:
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
        ", child, loli, teen, underage, young, schoolgirl"
        ", nude, naked, nipples, areola, pussy, penis, testicles, sex, intercourse, blowjob, fellatio, anal"
    )

# 闇の実験室（lab）: ネガは崩壊防止のみ、安全タグは付けない
if profile == "lab":
    try:
        from mufufu_config_lab import LAB_NEGATIVE_PROMPT

        MUFUFU_NEGATIVE_PROMPT = LAB_NEGATIVE_PROMPT
        print("[PROFILE] 闇の実験室（lab）: ネガ最小限・表現はモデルに委ねます")
    except ImportError:
        print("[WARN] mufufu_config_lab が見つかりません。通常ネガで続行します。")

# プロンプト要素（非露骨）
clothing_style = [
    "clear gyaru style",
    "pure gyaru style",
    "innocent gyaru style",
    "cute gyaru style",
]
bodies = ["slim body", "toned body", "athletic body", "fit body"]
breast_size = ["medium breasts", "large breasts", "D cup"]
hair_styles = ["long hair", "medium hair", "wavy hair", "straight hair", "black hair"]
skin_tone = ["pale skin", "fair skin"]
lighting = ["soft lighting", "natural lighting", "warm lighting", "dramatic lighting"]

if mode == "mufufu":
    # より刺激的・セクシー寄り（露骨な性表現は含めない：衣装・ポーズ・シチュを強化）
    outfits = [
        "lingerie",
        "lace lingerie",
        "silk lingerie",
        "sheer lingerie",
        "see-through negligee",
        "babydoll",
        "bodysuit",
        "garter belt",
        "fishnet stockings",
        "bikini",
        "micro bikini",
        "string bikini",
        "one-piece swimsuit",
        "short skirt",
        "miniskirt",
        "crop top and shorts",
        "tight dress",
        "low-cut top",
        "wet clothes",
        "transparent dress",
        "off-shoulder dress",
        "bra and panties",
        "corset",
    ]
    poses = [
        "lying on bed",
        "lying on back",
        "sitting on bed",
        "reclining",
        "standing",
        "kneeling",
        "leaning",
        "looking over shoulder",
        "from behind",
        "bent over",
        "arched back",
        "sprawling",
        "provocative pose",
        "teasing pose",
        "ass focus",
        "breast focus",
        "close-up",
        "upskirt angle",
    ]
    expressions = [
        "seductive",
        "sultry",
        "bedroom eyes",
        "confident",
        "playful",
        "inviting smile",
        "alluring",
        "mysterious smile",
        "passionate look",
        "desiring",
        "lustful eyes",
        "teasing expression",
    ]
    scenes = [
        "boudoir",
        "bedroom",
        "hotel room",
        "dim lighting",
        "candlelight",
        "silk sheets",
        "studio portrait",
        "intimate setting",
        "poolside",
        "hot tub",
        "bathroom",
        "shower",
        "morning after",
        "sultry atmosphere",
    ]
    extra_tags = [
        "adult woman",
        "20s",
        "makeup",
        "glossy lips",
        "cleavage",
        "deep cleavage",
        "stockings",
        "high heels",
        "thigh highs",
        "revealing",
        "sultry atmosphere",
        "sensual",
        "erotic mood",
        "suggestive",
        "tempting",
        "alluring pose",
    ]
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

# 闇の実験室（lab）: 裸・性行為系のプロンプト要素（profile=lab のときのみ使用・バリエーション多め）
if profile == "lab":
    outfits = [
        "nude",
        "naked",
        "nude body",
        "bare chest",
        "topless",
        "no clothes",
        "naked woman",
        "full nude",
        "see-through",
        "lingerie",
        "bra and panties",
        "stockings only",
        "nude on bed",
        "naked in bed",
        "wet nude",
        "shower nude",
        "spread legs nude",
        "bottomless",
        "topless only",
        "naked from behind",
        "exposed breasts",
        "exposed nipples",
        "visible pussy",
        "open legs",
    ]
    poses = [
        "lying on bed",
        "lying nude",
        "spread legs",
        "on all fours",
        "doggy position",
        "missionary",
        "cowgirl position",
        "sitting nude",
        "standing nude",
        "bent over",
        "from behind",
        "ass focus",
        "breast focus",
        "pussy focus",
        "close-up pussy",
        "penetration",
        "sex",
        "intercourse",
        "riding",
        "doggy style",
        "standing sex",
        "oral sex",
        "blowjob",
        "handjob",
        "masturbation",
        "fingering",
        "squatting nude",
        "kneeling nude",
        "legs up",
        "spread pussy",
    ]
    expressions = [
        "orgasm",
        "pleasure",
        "ecstasy",
        "lustful",
        "desiring",
        "seductive",
        "passionate",
        "ahegao",
        "bedroom eyes",
        "cum face",
        "moaning",
        "blushing",
        "tears of pleasure",
        "open mouth",
    ]
    scenes = [
        "bedroom",
        "bed",
        "sex scene",
        "intimate",
        "after sex",
        "hotel room",
        "nude in bed",
        "hardcore",
        "porn",
        "adult film",
        "bathroom",
        "shower sex",
        "kitchen sex",
        "couch",
        "floor",
        "mirror",
        "window",
        "morning sex",
        "night sex",
        "bondage scene",
        "dungeon",
        "sex dungeon",
        "orgy",
        "gangbang",
        "public sex",
        "outdoor sex",
    ]
    extra_tags = [
        "adult",
        "nsfw",
        "explicit",
        "nude",
        "naked",
        "nipples",
        "areola",
        "pussy",
        "vagina",
        "sex",
        "realistic",
        "uncensored",
        "1girl",
        "solo",
        "heterosexual",
        "vaginal",
        "cum",
        "cum on body",
        "creampie",
        "multiple orgasms",
        "penetration",
        "oral",
        "deep throat",
        "cum in mouth",
        "cum on face",
        "cum on breasts",
        "wet",
        "sweaty",
        "arousal",
        "horny",
        "lust",
        "bdsm",
        "bondage",
        "spread pussy",
        "open legs",
        "ass",
        "anal",
        "threesome",
        "double penetration",
    ]
    # lab用: 裸・半裸＋性行為を優先（このリストから70%で選択）
    LAB_FAVORED_OUTFITS = [
        "nude",
        "naked",
        "nude body",
        "bare chest",
        "topless",
        "no clothes",
        "naked woman",
        "full nude",
        "nude on bed",
        "naked in bed",
        "wet nude",
        "spread legs nude",
        "bottomless",
        "exposed breasts",
        "exposed nipples",
        "visible pussy",
        "open legs",
    ]
    LAB_FAVORED_POSES = [
        "penetration",
        "sex",
        "intercourse",
        "riding",
        "doggy style",
        "standing sex",
        "oral sex",
        "blowjob",
        "missionary",
        "cowgirl position",
        "doggy position",
        "on all fours",
        "legs up",
        "spread pussy",
        "handjob",
        "masturbation",
        "fingering",
    ]
    LAB_FAVORED_SCENES = [
        "bedroom",
        "bed",
        "sex scene",
        "intimate",
        "after sex",
        "nude in bed",
        "hardcore",
        "shower sex",
        "morning sex",
        "night sex",
    ]
    # lab 用スタイル（character で使用・バリエーション）
    clothing_style = [
        "realistic",
        "photorealistic",
        "hentai style",
        "erotic",
        "adult content",
        "uncensored",
        "hyperrealistic",
        "anime style nude",
        "3D render",
        "oil painting style",
        "cinematic",
    ]

print(f"利用可能なモデル: {len(available_models)}件")
print(f"利用可能なLoRA: {len(available_loras)}件")
print(
    f"生成数: {num_images}枚 | プロファイル: {profile}" + (" | 全モデル・全LoRA" if use_all else "")
)
if use_custom_prompt and custom_prompt_raw:
    print("[固定プロンプト] --prompt で指定したテキストを使用します（<lora:> は除去）")
print()

if not available_models:
    print("[ERROR] 利用可能なモデルが0件です。")
    print(f"  {COMFYUI_MODELS_DIR} に .safetensors または .ckpt を配置してください。")
    sys.exit(1)


def _check_comfyui_ready() -> bool:
    """ComfyUI が起動しており接続可能か確認する。"""
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ComfyUI 起動確認：接続できない場合はここで終了
print("ComfyUI 起動確認中...", end=" ", flush=True)
if not _check_comfyui_ready():
    print("❌ 失敗")
    print("")
    print("[ERROR] ComfyUI に接続できません。")
    print(f"  {COMFYUI_URL} が起動しているか確認してください。")
    print("  ブラウザで http://localhost:8188 を開けるか確認してから、再度実行してください。")
    sys.exit(1)
print("✅ OK")

# lab 時: 出力先フォルダを事前に作成（ComfyUI が subfolder に保存する前提）
if profile == "lab":
    lab_dir = OUTPUT_DIR / "lab"
    lab_dir.mkdir(parents=True, exist_ok=True)
    print(f"出力先: {lab_dir.resolve()}")
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

    # モデル選択（--prefer-new 時は新規モデルを50%優先、否则は学習好みを50%優先）
    new_models_available = [m for m in NEW_MODELS if m in available_models]
    if prefer_new and new_models_available and random.random() < 0.5:
        model = random.choice(new_models_available)
    elif learned_preferences.get("models") and random.random() < 0.5:
        learned_models_available = [
            m for m in learned_preferences["models"] if m in available_models
        ]
        if learned_models_available:
            model = random.choice(learned_models_available)
        else:
            model = random.choice(available_models)
    else:
        # lab時: アダルト向けモデルを45%で優先（pony/nude/BDSM等を含むモデル）
        if profile == "lab":
            preferred_models = [
                m
                for m in available_models
                if any(kw in m.lower() for kw in LAB_PREFERRED_MODEL_KEYWORDS)
            ]
            if preferred_models and random.random() < 0.45:
                model = random.choice(preferred_models)
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

    # LoRA選択（--use-all でなければモデル種別に合うLoRAに絞り、--prefer-new / 推奨組み合わせ・学習好みを反映）
    loras_for_model = filter_loras_for_model(available_loras, model, use_all=use_all)
    recommended_for_model = []
    for key, lora_list in (RECOMMENDED_MODEL_LORA_PAIRS or {}).items():
        if key.lower() in model.lower():
            recommended_for_model.extend(l for l in lora_list if l in loras_for_model)

    new_loras_available = [l for l in NEW_LORAS if l in loras_for_model]

    # lab時: LoRAを0本にしにくく、2〜3本を多めに（アダルト要素を強める）
    if profile == "lab":
        num_loras = random.choices([0, 1, 2, 3], weights=[10, 30, 40, 20])[0]
    else:
        num_loras = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
    loras = []
    if loras_for_model and num_loras > 0:
        pool = list(loras_for_model)
        # lab時: アダルト系LoRAを50%で1本以上含める
        adult_loras = (
            [l for l in pool if any(kw in l.lower() for kw in LAB_PREFERRED_LORA_KEYWORDS)]
            if profile == "lab"
            else []
        )
        if profile == "lab" and adult_loras and random.random() < 0.5:
            pick_one = random.choice(adult_loras)
            rest_pool = [l for l in pool if l != pick_one]
            need = num_loras - 1
            selected_loras = [pick_one]
            if need > 0 and rest_pool:
                selected_loras.extend(random.sample(rest_pool, min(need, len(rest_pool))))
        elif prefer_new and new_loras_available and random.random() < 0.5:
            # 新規LoRAを1本以上含める
            pick = min(num_loras, len(new_loras_available))
            selected_loras = random.sample(new_loras_available, pick)
            need = num_loras - len(selected_loras)
            if need > 0:
                rest = [l for l in pool if l not in selected_loras]
                if rest:
                    selected_loras.extend(random.sample(rest, min(need, len(rest))))
        elif learned_preferences.get("loras") and random.random() < 0.6:
            learned_loras_available = [l for l in learned_preferences["loras"] if l in pool]
            if learned_loras_available:
                selected_loras = random.sample(
                    learned_loras_available, min(num_loras, len(learned_loras_available))
                )
            else:
                selected_loras = random.sample(pool, min(num_loras, len(pool)))
        elif recommended_for_model and random.random() < 0.4:
            # 推奨モデル＋LoRA組み合わせを優先（1本は推奨から）
            pick = min(num_loras, len(recommended_for_model))
            selected_loras = random.sample(recommended_for_model, pick)
            need = num_loras - len(selected_loras)
            if need > 0:
                rest = [l for l in pool if l not in selected_loras]
                if rest:
                    selected_loras.extend(random.sample(rest, min(need, len(rest))))
        else:
            selected_loras = random.sample(pool, min(num_loras, len(pool)))

        for lora_name in selected_loras:
            # lab時: 強度をやや高めにしてアダルト表現を効かせる
            if profile == "lab":
                base_strength = 0.70 if len(loras) == 0 else 0.60
                lora_strength = round(random.uniform(base_strength, base_strength + 0.18), 2)
                lora_strength = min(0.90, max(0.50, lora_strength))
            else:
                base_strength = 0.65 if len(loras) == 0 else 0.55
                lora_strength = round(random.uniform(base_strength, base_strength + 0.15), 2)
                lora_strength = min(0.85, max(0.45, lora_strength))
            loras.append((lora_name, lora_strength))

    # プロンプト生成（--prompt 指定時は固定テキストを使用）
    if use_custom_prompt and custom_prompt_raw:
        # <lora:名前:強度> は ComfyUI ではノードで適用するため除去（重み付きタグはそのまま）
        prompt = re.sub(r"<lora:[^>]+>", "", custom_prompt_raw).strip()
        prompt = re.sub(r",\s*,", ",", prompt)  # 連続カンマを1つに
        negative_prompt_for_workflow = (
            custom_negative_raw if custom_negative_raw else MUFUFU_NEGATIVE_PROMPT
        )
    else:
        negative_prompt_for_workflow = MUFUFU_NEGATIVE_PROMPT
    # 通常のランダムプロンプト構築
    if not (use_custom_prompt and custom_prompt_raw):
        # lab 時: 裸・半裸＋性行為を70%で優先しつつ、タグ数は控えめで崩れを防ぐ
        if profile == "lab":
            o_list = LAB_FAVORED_OUTFITS if random.random() < 0.7 else outfits
            outfit_part = random.choice(o_list)
            if random.random() < 0.5:
                o2 = LAB_FAVORED_OUTFITS if random.random() < 0.7 else outfits
                outfit_part = outfit_part + ", " + random.choice(o2)
            p_list = LAB_FAVORED_POSES if random.random() < 0.7 else poses
            pose_part = random.choice(p_list)
            if random.random() < 0.45:
                p2 = LAB_FAVORED_POSES if random.random() < 0.7 else poses
                pose_part = pose_part + ", " + random.choice(p2)
            extra_sample = random.sample(extra_tags, min(random.randint(4, 7), len(extra_tags)))
        else:
            outfit_part = random.choice(outfits)
            pose_part = random.choice(poses)
            extra_sample = list(extra_tags)

        # lab時: 65%で性行為シーン（ベッド・sex scene等）を優先
        if profile == "lab":
            scene_choice = (
                random.choice(LAB_FAVORED_SCENES) if random.random() < 0.65 else random.choice(scenes)
            )
        else:
            scene_choice = random.choice(scenes)

        if build_ordered_prompt and ANATOMY_POSITIVE_TAGS and QUALITY_TAGS:
            sections = {
                "anatomy": ANATOMY_POSITIVE_TAGS,
                "quality": QUALITY_TAGS,
                "character": ", ".join(
                    [
                        "Japanese",
                        "Japanese woman",
                        "1girl",
                        "solo",
                        random.choice(clothing_style),
                        random.choice(bodies),
                        random.choice(breast_size),
                        random.choice(skin_tone),
                        *extra_sample,
                    ]
                ),
                "outfit": outfit_part,
                "pose": pose_part,
                "expression": random.choice(expressions),
                "body": "perfect proportions, correct anatomy, beautiful, gorgeous, stunning",
                "scene": ", ".join([scene_choice, random.choice(hair_styles)]),
                "lighting": random.choice(lighting),
                "trailing_quality": "realistic, photorealistic, high quality, detailed, sharp focus, 8k uhd",
            }
            prompt = build_ordered_prompt(sections)
        else:
            prompt_parts = [
                "Japanese",
                "Japanese woman",
                "1girl",
                "solo",
                random.choice(clothing_style),
                outfit_part,
                pose_part,
                random.choice(expressions),
                random.choice(bodies),
                random.choice(breast_size),
                random.choice(skin_tone),
                *extra_sample,
                "perfect proportions",
                "correct anatomy",
                "beautiful",
                "gorgeous",
                "stunning",
                scene_choice,
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

        if learned_preferences.get("params", {}).get("width") and learned_preferences.get(
            "params", {}
        ).get("height"):
            width = learned_preferences["params"]["width"]
            height = learned_preferences["params"]["height"]
        else:
            width, height = random.choice([(1024, 1024), (1024, 1280), (1280, 1024)])
    else:
        if learned_preferences.get("params", {}).get("steps"):
            steps = learned_preferences["params"]["steps"]
        else:
            steps = random.choice([60, 65, 70, 75])

        if learned_preferences.get("params", {}).get("width") and learned_preferences.get(
            "params", {}
        ).get("height"):
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
        sampler = random.choice(
            ["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpmpp_2m"]
        )

    if learned_preferences.get("params", {}).get("scheduler"):
        scheduler = learned_preferences["params"]["scheduler"]
    else:
        scheduler = random.choice(["normal", "karras", "exponential"])

    seed = random.randint(1, 2**32 - 1)

    workflow = create_workflow_with_multiple_loras(
        prompt=prompt,
        negative_prompt=negative_prompt_for_workflow,
        model=model,
        loras=loras if loras else None,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        sampler=sampler,
        scheduler=scheduler,
        seed=seed,
        output_subfolder="lab" if profile == "lab" else None,
    )

    lora_info = ""
    if loras:
        lora_names = [l[0][:20] for l in loras]
        lora_info = f" + LoRA:{'+'.join(lora_names)}"

    print(f"{model[:35]}{lora_info}", flush=True)
    print(f"  {width}x{height}, {steps}steps, CFG:{guidance_scale}, Seed:{seed}", flush=True)

    try:
        payload = {"prompt": workflow}
        response = _send_prompt_with_retry(payload)
        if response is None:
            failed_count += 1
            print(
                "  [ERROR] リクエスト送信に失敗しました（接続・タイムアウトの可能性）", flush=True
            )
            print()
            time.sleep(1)
            continue

        if response.status_code == 200:
            result = response.json()
            err = result.get("error") if isinstance(result, dict) else None
            if err:
                failed_count += 1
                msg = _format_comfyui_error(err)
                print(f"  [ERROR] ComfyUI: {msg}", flush=True)
            elif result.get("prompt_id"):
                prompt_id = result["prompt_id"]
                prompt_ids.append(prompt_id)
                success_count += 1
                print(f"  [OK] {prompt_id}", flush=True)

                # 実際の出力ファイル名を取得（--no-wait の場合はスキップ）
                if no_wait:
                    output_filenames = []
                    status_extra = None
                else:
                    output_filenames = wait_for_output_filenames(
                        prompt_id, timeout=wait_timeout_sec
                    )
                    status_extra = "pending_filename_fetch" if not output_filenames else None

                # 出力ファイル名（subfolder付きの場合あり）を実ファイルパスへ解決
                output_paths_list = [
                    str(_resolve_output_path(fname, profile)) for fname in (output_filenames or [])
                ]

                # 生成メタデータを保存（profile で通常/実験室を区別）
                gen_metadata = {
                    "model": model,
                    "loras": [{"name": l[0], "strength": l[1]} for l in loras] if loras else [],
                    "prompt": prompt,
                    "negative_prompt": negative_prompt_for_workflow,
                    "steps": steps,
                    "guidance_scale": guidance_scale,
                    "width": width,
                    "height": height,
                    "sampler": sampler,
                    "scheduler": scheduler,
                    "seed": seed,
                    "prompt_id": prompt_id,
                    "output_filenames": output_filenames if output_filenames else [],
                    "output_paths": output_paths_list,
                    "profile": profile,
                }
                if status_extra:
                    gen_metadata["status"] = status_extra
                generation_metadata[prompt_id] = gen_metadata

                # A相当: 新規生成分はサムネを先に作っておく（UIの初回表示を軽くする）
                if output_filenames:
                    for fname in output_filenames:
                        try:
                            src_path = _resolve_output_path(fname, profile)
                            _ensure_thumbnail(src_path)
                        except Exception:
                            pass
            else:
                if not err:
                    failed_count += 1
                    print("  [ERROR] プロンプトIDが取得できませんでした", flush=True)
        else:
            failed_count += 1
            try:
                body = response.text[:500] if response.text else ""
                print(f"  [ERROR] HTTP {response.status_code} {body}", flush=True)
            except Exception:
                print(f"  [ERROR] HTTP {response.status_code}", flush=True)
    except Exception as e:
        failed_count += 1
        print(f"  [ERROR] {e}", flush=True)

    print()
    time.sleep(1)  # レート制限対策

# 生成メタデータを保存
if generation_metadata:
    # 既存のメタデータを読み込んでマージ
    existing_metadata = {}
    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)
        except Exception as e:
            print(f"⚠️ 既存メタデータの読み込みエラー: {e}")

    existing_metadata.update(generation_metadata)

    # 保存
    GENERATION_METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(GENERATION_METADATA_DB, "w", encoding="utf-8") as f:
            json.dump(existing_metadata, f, ensure_ascii=False, indent=2)
        print(f"✅ 生成メタデータを保存しました: {len(generation_metadata)}件")
    except Exception as e:
        print(f"⚠️ 生成メタデータの保存エラー: {e}")

print("=" * 60)
print(f"生成リクエスト完了: 成功 {success_count}件 / 失敗 {failed_count}件")
print("=" * 60)
print("画像はComfyUIの出力フォルダに保存されます。")
if no_wait:
    print("（--no-wait 使用のため、画像はComfyUIの出力フォルダで確認してください）")
print("評価UIで評価すると、次回の生成に反映されます。")
