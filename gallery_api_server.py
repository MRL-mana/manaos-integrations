#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 ManaOS Gallery API Server
画像生成・管理APIサーバー（ComfyUI連携）
"""

import os
import json
import uuid
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
    from manaos_timeout_config import get_timeout_config
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    get_logger = lambda name: logging.getLogger(name)
    class ManaOSErrorHandler:
        def handle_exception(self, e, **kwargs):
            pass
    ErrorCategory = type('ErrorCategory', (), {})
    ErrorSeverity = type('ErrorSeverity', (), {})
    def get_timeout_config():
        return {"api_call": 30.0, "workflow_execution": 300.0}

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("GalleryAPI")

# Flaskアプリの初期化
app = Flask(__name__)
CORS(app)

# 設定
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
GALLERY_PORT = int(os.getenv("GALLERY_PORT", 5559))
IMAGES_DIR = Path(os.getenv("GALLERY_IMAGES_DIR", "gallery_images"))
IMAGES_DIR.mkdir(exist_ok=True)

# モデルパス設定
MANA_MODELS_DIR = Path(os.getenv("MANA_MODELS_DIR", "C:/mana_workspace/models"))
COMFYUI_MODELS_DIR = Path(os.getenv("COMFYUI_MODELS_DIR", "C:/ComfyUI/models/checkpoints"))

# ジョブ管理
jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()

# ムフフモード設定のインポート（身体崩れ対策強化版）
try:
    from mufufu_config import (
        MUFUFU_NEGATIVE_PROMPT,
        ANATOMY_POSITIVE_TAGS,
        OPTIMIZED_PARAMS
    )
    logger.info("✅ ムフフ設定ファイルを読み込みました（身体崩れ対策強化版）")
except ImportError:
    # フォールバック: 旧バージョン（互換性のため）
    MUFUFU_NEGATIVE_PROMPT = "clothes, clothing, dress, shirt, pants, skirt, underwear, bra, panties, swimsuit, bikini, uniform, costume, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, bad proportions, duplicate, ugly, deformed, poorly drawn, bad body, out of frame, extra limbs, disfigured, mutation, mutated, mutilated, bad art, bad structure"
    ANATOMY_POSITIVE_TAGS = ""
    OPTIMIZED_PARAMS = {}
    logger.warning("⚠️ ムフフ設定ファイルが見つかりません。旧バージョンを使用します。")

# 自動反省・改善システムのインポート
try:
    from auto_reflection_improvement import get_auto_reflection_system
    AUTO_REFLECTION_AVAILABLE = True
    logger.info("✅ 自動反省・改善システムを読み込みました")
except ImportError:
    AUTO_REFLECTION_AVAILABLE = False
    logger.warning("⚠️ 自動反省・改善システムが見つかりません。評価機能は無効です。")

# デフォルトで日本人を生成するためのプロンプトプレフィックス
DEFAULT_JAPANESE_PROMPT = "Japanese, Japanese woman, 日本人, 1girl, beautiful face, black hair, brown eyes"


def get_available_models() -> List[str]:
    """利用可能なモデルリストを取得"""
    models = []

    # ComfyUIのcheckpointsディレクトリを確認
    logger.debug(f"モデル検索: COMFYUI_MODELS_DIR={COMFYUI_MODELS_DIR}, exists={COMFYUI_MODELS_DIR.exists()}")
    if COMFYUI_MODELS_DIR.exists():
        for model_file in COMFYUI_MODELS_DIR.glob("*.safetensors"):
            if model_file.name != "put_checkpoints_here":
                models.append(model_file.name)
        logger.debug(f"ComfyUIディレクトリから {len(models)} 個のモデルを発見")

    # ManaOSのmodelsディレクトリも確認
    logger.debug(f"モデル検索: MANA_MODELS_DIR={MANA_MODELS_DIR}, exists={MANA_MODELS_DIR.exists()}")
    if MANA_MODELS_DIR.exists():
        mana_models = []
        for model_file in MANA_MODELS_DIR.glob("*.safetensors"):
            if model_file.name not in models:
                models.append(model_file.name)
                mana_models.append(model_file.name)
        logger.debug(f"ManaOSディレクトリから {len(mana_models)} 個の追加モデルを発見")

    logger.info(f"利用可能なモデル総数: {len(models)}")
    return models


def find_model_path(model_name: str) -> Optional[str]:
    """モデルファイルのパスを検索"""
    # ComfyUIのcheckpointsディレクトリを確認
    comfyui_path = COMFYUI_MODELS_DIR / model_name
    if comfyui_path.exists():
        logger.debug(f"モデル発見: {model_name} at {comfyui_path}")
        return model_name  # ComfyUIが直接参照できる
    else:
        logger.debug(f"モデル未発見: {model_name} at {comfyui_path} (存在: {comfyui_path.exists()})")

    # ManaOSのmodelsディレクトリを確認
    mana_path = MANA_MODELS_DIR / model_name
    if mana_path.exists():
        # シンボリックリンクを作成（管理者権限が必要な場合はコピー）
        try:
            link_path = COMFYUI_MODELS_DIR / model_name
            if not link_path.exists():
                import shutil
                shutil.copy2(mana_path, link_path)
                logger.info(f"モデルをコピー: {mana_path} -> {link_path}")
            return model_name
        except Exception as e:
            logger.warning(f"モデルコピー失敗: {e}")
            # 直接パスを返す（ComfyUIが対応していない可能性あり）
            return str(mana_path)

    return None


def create_comfyui_workflow(
    prompt: str,
    negative_prompt: str = "",
    model: str = "realisian_v60.safetensors",
    steps: int = 50,
    guidance_scale: float = 7.5,
    width: int = 768,
    height: int = 1024,
    sampler: str = "euler",
    scheduler: str = "normal",
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """ComfyUIワークフローを作成"""
    # モデルパスを確認
    logger.info(f"モデル検索開始: {model}")
    model_path = find_model_path(model)
    if not model_path:
        # デフォルトモデルを探す
        logger.info("指定モデルが見つからないため、利用可能なモデルを検索中...")
        available_models = get_available_models()
        if available_models:
            model_path = available_models[0]
            logger.warning(f"モデル '{model}' が見つかりません。代わりに '{model_path}' を使用します。")
        else:
            # デバッグ情報を追加
            logger.error(f"モデル検索失敗: model={model}")
            logger.error(f"COMFYUI_MODELS_DIR={COMFYUI_MODELS_DIR}, exists={COMFYUI_MODELS_DIR.exists()}")
            logger.error(f"MANA_MODELS_DIR={MANA_MODELS_DIR}, exists={MANA_MODELS_DIR.exists()}")
            if COMFYUI_MODELS_DIR.exists():
                try:
                    files = list(COMFYUI_MODELS_DIR.glob("*.safetensors"))
                    logger.error(f"COMFYUIディレクトリ内のファイル数: {len(files)}")
                except Exception as e:
                    logger.error(f"ディレクトリ読み取りエラー: {e}")
            raise ValueError(f"利用可能なモデルが見つかりません。指定モデル: {model}, 検索ディレクトリ: {COMFYUI_MODELS_DIR}")
    else:
        model_path = model
        logger.info(f"モデル検索成功: {model_path}")

    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_path
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "4": {
            "inputs": {
                "seed": seed if seed is not None else int(time.time() * 1000) % (2**32),
                "steps": steps,
                "cfg": guidance_scale,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["6", 0]
            },
            "class_type": "SaveImage"
        }
    }
    return workflow


def submit_to_comfyui(workflow: Dict[str, Any]) -> Optional[str]:
    """ComfyUIにワークフローを送信"""
    try:
        client_id = str(uuid.uuid4())
        payload = {
            "prompt": workflow,
            "client_id": client_id
        }

        response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json=payload,
            timeout=30.0
        )

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"ComfyUI送信エラー ({response.status_code}): {error_detail}")
            try:
                error_json = response.json()
                logger.error(f"エラー詳細: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
            except (ValueError, json.JSONDecodeError):
                logger.debug(f"エラーレスポンスのJSON解析失敗: {error_detail[:200]}")
            return None

        result = response.json()
        prompt_id = result.get("prompt_id")
        logger.info(f"ComfyUIにワークフロー送信: prompt_id={prompt_id}")
        return prompt_id
    except requests.exceptions.RequestException as e:
        logger.error(f"ComfyUI送信エラー (RequestException): {e}")
        return None
    except Exception as e:
        logger.error(f"ComfyUI送信エラー: {e}", exc_info=True)
        return None


def check_comfyui_history(prompt_id: str, max_wait: int = 300) -> Optional[str]:
    """ComfyUIの履歴を確認して画像ファイル名を取得"""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{COMFYUI_URL}/history/{prompt_id}",
                timeout=10.0
            )

            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for image_info in node_output["images"]:
                                filename = image_info.get("filename")
                                if filename:
                                    return filename

            # 履歴にない場合は、出力ディレクトリを確認
            comfyui_output = Path(os.getenv("COMFYUI_OUTPUT_DIR", "C:/ComfyUI/output"))
            if comfyui_output.exists():
                # 最新のファイルを探す
                image_files = sorted(
                    comfyui_output.glob("*.png"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                if image_files:
                    return image_files[0].name

            time.sleep(2)
        except Exception as e:
            logger.warning(f"履歴確認エラー: {e}")
            time.sleep(2)

    return None


def auto_regenerate(
    job_id: str,
    original_prompt: str,
    original_negative_prompt: str,
    original_model: str,
    original_parameters: Dict[str, Any],
    improvement: Dict[str, Any],
    original_reflection: Dict[str, Any],
    max_retries: int = 2
):
    """
    自動再生成（改善提案に基づいて）
    
    Args:
        job_id: 元のジョブID
        original_prompt: 元のプロンプト
        original_negative_prompt: 元のネガティブプロンプト
        original_model: 元のモデル
        original_parameters: 元のパラメータ
        improvement: 改善提案
        original_reflection: 元の評価結果
        max_retries: 最大再生成回数
    """
    def perform_auto_regeneration():
        try:
            improved_prompt = improvement.get("improved_prompt", original_prompt)
            improved_negative_prompt = improvement.get("improved_negative_prompt", original_negative_prompt)
            improved_parameters = improvement.get("improved_parameters", original_parameters)
            
            logger.info(f"[全自動再生成] 改善されたパラメータで再生成を開始...")
            logger.info(f"  改善理由: {improvement.get('reason', '')}")
            logger.info(f"  プロンプト改善: {len(improved_prompt)}文字")
            logger.info(f"  パラメータ改善: steps {original_parameters.get('steps')} -> {improved_parameters.get('steps')}")
            
            # 再生成リクエスト
            regenerate_data = {
                "prompt": improved_prompt,
                "negative_prompt": improved_negative_prompt,
                "model": original_model,
                "steps": improved_parameters.get("steps", original_parameters.get("steps", 50)),
                "guidance_scale": improved_parameters.get("guidance_scale", original_parameters.get("guidance_scale", 7.5)),
                "width": improved_parameters.get("width", original_parameters.get("width", 1024)),
                "height": improved_parameters.get("height", original_parameters.get("height", 1024)),
                "sampler": improved_parameters.get("sampler", original_parameters.get("sampler", "dpmpp_2m")),
                "scheduler": improved_parameters.get("scheduler", original_parameters.get("scheduler", "karras")),
                "seed": improved_parameters.get("seed", original_parameters.get("seed")),
                "mufufu_mode": True,
                "auto_reflection": True  # 再生成も自動評価
            }
            
            # ワークフローを作成
            workflow = create_comfyui_workflow(
                prompt=regenerate_data["prompt"],
                negative_prompt=regenerate_data["negative_prompt"],
                model=regenerate_data["model"],
                steps=regenerate_data["steps"],
                guidance_scale=regenerate_data["guidance_scale"],
                width=regenerate_data["width"],
                height=regenerate_data["height"],
                sampler=regenerate_data["sampler"],
                scheduler=regenerate_data["scheduler"],
                seed=regenerate_data.get("seed")
            )
            
            # ComfyUIに送信
            new_prompt_id = submit_to_comfyui(workflow)
            if not new_prompt_id:
                logger.error("[全自動再生成] ComfyUIへの送信に失敗しました")
                return
            
            # 新しいジョブを作成（改善版として）
            new_job_id = f"{job_id}_improved_{int(time.time())}"
            with jobs_lock:
                jobs[new_job_id] = {
                    "job_id": new_job_id,
                    "prompt_id": new_prompt_id,
                    "prompt": improved_prompt,
                    "model": original_model,
                    "status": "processing",
                    "created_at": datetime.now().isoformat(),
                    "filename": None,
                    "error": None,
                    "parent_job_id": job_id,
                    "regeneration_type": "auto_improvement"
                }
            
            logger.info(f"[全自動再生成] 新しいジョブ作成: {new_job_id}")
            
            # 再生成完了を監視
            def monitor_regeneration():
                filename = check_comfyui_history(new_prompt_id)
                if filename:
                    gallery_filename = copy_image_to_gallery(filename)
                    if gallery_filename:
                        # メタデータを保存
                        metadata = {
                            "job_id": new_job_id,
                            "parent_job_id": job_id,
                            "prompt_id": new_prompt_id,
                            "prompt": improved_prompt,
                            "negative_prompt": improved_negative_prompt,
                            "model": original_model,
                            "steps": improved_parameters.get("steps"),
                            "guidance_scale": improved_parameters.get("guidance_scale"),
                            "width": improved_parameters.get("width"),
                            "height": improved_parameters.get("height"),
                            "sampler": improved_parameters.get("sampler"),
                            "scheduler": improved_parameters.get("scheduler"),
                            "seed": improved_parameters.get("seed"),
                            "mufufu_mode": True,
                            "regeneration_type": "auto_improvement",
                            "improvement_reason": improvement.get("reason"),
                            "created_at": datetime.now().isoformat()
                        }
                        metadata_path = IMAGES_DIR / f"{gallery_filename}.json"
                        with open(metadata_path, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=2)
                        
                        # 改善版も自動評価
                        if AUTO_REFLECTION_AVAILABLE:
                            try:
                                auto_system = get_auto_reflection_system()
                                image_path = str(IMAGES_DIR / gallery_filename)
                                
                                new_reflection = auto_system.process_generated_image(
                                    image_path=image_path,
                                    prompt=improved_prompt,
                                    negative_prompt=improved_negative_prompt,
                                    model=original_model,
                                    parameters=improved_parameters,
                                    auto_improve=False,  # 再生成の評価では自動改善は無効（無限ループ防止）
                                    threshold=0.7
                                )
                                
                                # 改善の確認
                                original_score = original_reflection['evaluation']['overall_score']
                                new_score = new_reflection['evaluation']['overall_score']
                                score_improvement = new_score - original_score
                                
                                logger.info(f"[全自動再生成] 改善版評価完了")
                                logger.info(f"  元のスコア: {original_score:.2f}")
                                logger.info(f"  改善版スコア: {new_score:.2f}")
                                logger.info(f"  スコア改善: {score_improvement:+.2f}")
                                
                                # 学習データに記録
                                if score_improvement > 0:
                                    logger.info(f"[学習] 改善成功を記録: {score_improvement:.2f}向上")
                                    try:
                                        from auto_reflection_improvement import ImageEvaluation, ImprovementPlan
                                        from dataclasses import asdict
                                        
                                        # 元の評価オブジェクトを再構築（学習用）
                                        orig_eval = original_reflection.get('evaluation', {})
                                        orig_evaluation = ImageEvaluation(
                                            image_path=orig_eval.get('image_path', ''),
                                            prompt=orig_eval.get('prompt', ''),
                                            negative_prompt=orig_eval.get('negative_prompt', ''),
                                            model=orig_eval.get('model', ''),
                                            parameters=orig_eval.get('parameters', {}),
                                            overall_score=orig_eval.get('overall_score', 0),
                                            anatomy_score=orig_eval.get('anatomy_score', 0),
                                            quality_score=orig_eval.get('quality_score', 0),
                                            prompt_match_score=orig_eval.get('prompt_match_score', 0),
                                            anatomy_issues=orig_eval.get('anatomy_issues', []),
                                            quality_issues=orig_eval.get('quality_issues', []),
                                            prompt_mismatches=orig_eval.get('prompt_mismatches', []),
                                            improvements=orig_eval.get('improvements', [])
                                        )
                                        
                                        # 改善計画オブジェクトを再構築
                                        improvement_plan = ImprovementPlan(
                                            original_prompt=improvement.get('original_prompt', ''),
                                            improved_prompt=improvement.get('improved_prompt', ''),
                                            original_negative_prompt=improvement.get('original_negative_prompt', ''),
                                            improved_negative_prompt=improvement.get('improved_negative_prompt', ''),
                                            original_parameters=improvement.get('original_parameters', {}),
                                            improved_parameters=improvement.get('improved_parameters', {}),
                                            reason=improvement.get('reason', ''),
                                            expected_improvement=improvement.get('expected_improvement', 0)
                                        )
                                        
                                        # 新しい評価オブジェクトを再構築
                                        new_eval = new_reflection.get('evaluation', {})
                                        new_evaluation = ImageEvaluation(
                                            image_path=new_eval.get('image_path', ''),
                                            prompt=new_eval.get('prompt', ''),
                                            negative_prompt=new_eval.get('negative_prompt', ''),
                                            model=new_eval.get('model', ''),
                                            parameters=new_eval.get('parameters', {}),
                                            overall_score=new_eval.get('overall_score', 0),
                                            anatomy_score=new_eval.get('anatomy_score', 0),
                                            quality_score=new_eval.get('quality_score', 0),
                                            prompt_match_score=new_eval.get('prompt_match_score', 0),
                                            anatomy_issues=new_eval.get('anatomy_issues', []),
                                            quality_issues=new_eval.get('quality_issues', []),
                                            prompt_mismatches=new_eval.get('prompt_mismatches', []),
                                            improvements=new_eval.get('improvements', [])
                                        )
                                        
                                        auto_system.improver.learn_from_result(
                                            evaluation=orig_evaluation,
                                            improvement=improvement_plan,
                                            new_evaluation=new_evaluation
                                        )
                                    except Exception as learn_error:
                                        logger.warning(f"[学習エラー] {learn_error}")
                                else:
                                    logger.warning(f"[学習] 改善失敗を記録: スコアが低下（{score_improvement:.2f}）")
                                else:
                                    logger.warning(f"[学習] 改善失敗を記録: スコアが低下（{score_improvement:.2f}）")
                                
                                # ジョブステータスを更新
                                with jobs_lock:
                                    if new_job_id in jobs:
                                        jobs[new_job_id]["status"] = "completed"
                                        jobs[new_job_id]["filename"] = gallery_filename
                                        jobs[new_job_id]["metadata"] = metadata
                                        jobs[new_job_id]["reflection"] = new_reflection
                                        jobs[new_job_id]["comparison"] = {
                                            "original_score": original_score,
                                            "improved_score": new_score,
                                            "score_improvement": score_improvement,
                                            "improvement_reason": improvement.get("reason")
                                        }
                                        
                                        # 元のジョブに改善版ジョブIDを記録
                                        with jobs_lock:
                                            if job_id in jobs:
                                                if "improved_jobs" not in jobs[job_id]:
                                                    jobs[job_id]["improved_jobs"] = []
                                                jobs[job_id]["improved_jobs"].append({
                                                    "job_id": new_job_id,
                                                    "score_improvement": score_improvement,
                                                    "improved_score": new_score
                                                })
                                                logger.info(f"[全自動再生成] 元のジョブ({job_id})に改善版ジョブ({new_job_id})を記録")
                            except Exception as e:
                                logger.error(f"[全自動再生成評価エラー] {e}", exc_info=True)
                        
                        # ジョブステータスを更新
                        with jobs_lock:
                            if new_job_id in jobs:
                                jobs[new_job_id]["status"] = "completed"
                                jobs[new_job_id]["filename"] = gallery_filename
                                jobs[new_job_id]["metadata"] = metadata
                else:
                    with jobs_lock:
                        if new_job_id in jobs:
                            jobs[new_job_id]["status"] = "failed"
                            jobs[new_job_id]["error"] = "再生成がタイムアウトしました"
            
            # 再生成を監視（バックグラウンド）
            regenerate_thread = threading.Thread(target=monitor_regeneration, daemon=True)
            regenerate_thread.start()
            
        except Exception as e:
            logger.error(f"[全自動再生成エラー] {e}", exc_info=True)
    
    # バックグラウンドで自動再生成を実行
    regenerate_thread = threading.Thread(target=perform_auto_regeneration, daemon=True)
    regenerate_thread.start()


def copy_image_to_gallery(filename: str) -> Optional[str]:
    """ComfyUIの出力画像をギャラリーディレクトリにコピー"""
    try:
        comfyui_output = Path(os.getenv("COMFYUI_OUTPUT_DIR", "C:/ComfyUI/output"))
        source_path = comfyui_output / filename

        if not source_path.exists():
            # ファイル名のみの場合、パスを探す
            for ext in [".png", ".jpg", ".jpeg"]:
                test_path = comfyui_output / f"{filename}{ext}"
                if test_path.exists():
                    source_path = test_path
                    filename = test_path.name
                    break

        if not source_path.exists():
            logger.error(f"画像ファイルが見つかりません: {filename}")
            return None

        # ギャラリーディレクトリにコピー
        gallery_filename = f"{uuid.uuid4()}_{filename}"
        dest_path = IMAGES_DIR / gallery_filename
        shutil.copy2(source_path, dest_path)

        logger.info(f"画像をコピー: {source_path} -> {dest_path}")
        return gallery_filename
    except Exception as e:
        logger.error(f"画像コピーエラー: {e}")
        return None


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    try:
        # ComfyUIの接続確認
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5.0)
        comfyui_available = response.status_code == 200
    except:
        comfyui_available = False

    return jsonify({
        "status": "ok",
        "service": "gallery_api",
        "comfyui_available": comfyui_available,
        "comfyui_url": COMFYUI_URL,
        "images_dir": str(IMAGES_DIR),
        "jobs_count": len(jobs)
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    """画像生成ジョブを開始"""
    try:
        data = request.json
        prompt = data.get("prompt")
        model = data.get("model", "realisian_v60.safetensors")
        steps = data.get("steps", 50)
        guidance_scale = data.get("guidance_scale", 7.5)
        width = data.get("width", 768)
        height = data.get("height", 1024)
        sampler = data.get("sampler", "dpmpp_2m")
        scheduler = data.get("scheduler", "karras")
        mufufu_mode = data.get("mufufu_mode", False)
        negative_prompt = data.get("negative_prompt", "")
        seed = data.get("seed", None)  # seedが指定されていない場合はNone（ランダム）

        if not prompt:
            return jsonify({
                "success": False,
                "error": "プロンプトが指定されていません"
            }), 400

        # プロンプトの前処理：重複要素の削除と整理
        prompt_parts = [p.strip() for p in prompt.split(",")]
        seen = set()
        unique_parts = []
        for part in prompt_parts:
            part_lower = part.lower().strip()
            if part_lower and part_lower not in seen:
                seen.add(part_lower)
                unique_parts.append(part)
        prompt = ", ".join(unique_parts)

        # デフォルトで日本人を生成する設定（プロンプトに日本人関連のキーワードがない場合）
        japanese_keywords = ["japanese", "日本人", "japan", "asian", "asian woman"]
        prompt_lower = prompt.lower()
        has_japanese_keyword = any(keyword in prompt_lower for keyword in japanese_keywords)

        if not has_japanese_keyword:
            # プロンプトの先頭に日本人タグを追加（重複チェック済みなので安全）
            prompt = f"{DEFAULT_JAPANESE_PROMPT}, {prompt}"
            logger.info(f"日本人タグを自動追加: {prompt}")

        # ムフフモードの場合、ネガティブプロンプトとポジティブプロンプトを強化
        if mufufu_mode:
            # ネガティブプロンプトを追加（身体崩れ対策強化版）
            if negative_prompt:
                negative_prompt = f"{negative_prompt}, {MUFUFU_NEGATIVE_PROMPT}"
            else:
                negative_prompt = MUFUFU_NEGATIVE_PROMPT
            
            # ポジティブプロンプトに身体崩れ対策タグを追加（重要）
            if ANATOMY_POSITIVE_TAGS:
                prompt = f"{ANATOMY_POSITIVE_TAGS}, {prompt}"
                logger.info("✅ ムフフモード: 身体崩れ対策タグをポジティブプロンプトに追加")
            
            # パラメータの最適化（身体崩れを減らすため）
            if OPTIMIZED_PARAMS:
                # stepsが指定されていない、または30未満の場合は最適化
                if not steps or steps < 30:
                    steps = OPTIMIZED_PARAMS.get("steps", 50)
                    logger.info(f"✅ ムフフモード: stepsを最適化 ({steps})")
                
                # guidance_scaleが指定されていない場合は最適化
                if not guidance_scale:
                    guidance_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
                    logger.info(f"✅ ムフフモード: guidance_scaleを最適化 ({guidance_scale})")
                
                # 解像度が低い場合は警告
                if width < OPTIMIZED_PARAMS.get("min_width", 1024) or height < OPTIMIZED_PARAMS.get("min_height", 1024):
                    logger.warning(f"⚠️ ムフフモード: 解像度が低いと身体崩れが増える可能性があります ({width}x{height})")

        # ワークフローを作成
        workflow = create_comfyui_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            steps=steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            sampler=sampler,
            scheduler=scheduler,
            seed=seed
        )

        # ComfyUIに送信
        prompt_id = submit_to_comfyui(workflow)
        if not prompt_id:
            return jsonify({
                "success": False,
                "error": "ComfyUIへの送信に失敗しました"
            }), 500

        # ジョブを作成
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "job_id": job_id,
                "prompt_id": prompt_id,
                "prompt": prompt,
                "model": model,
                "status": "processing",
                "created_at": datetime.now().isoformat(),
                "filename": None,
                "error": None
            }

        # バックグラウンドで画像生成を監視
        def monitor_generation():
            filename = check_comfyui_history(prompt_id)
            if filename:
                gallery_filename = copy_image_to_gallery(filename)
                if gallery_filename:
                    # プロンプト情報をメタデータとして保存
                    metadata = {
                        "job_id": job_id,
                        "prompt_id": prompt_id,
                        "prompt": prompt,
                        "original_prompt": data.get("prompt"),  # 元のプロンプト（日本人タグ追加前）
                        "negative_prompt": negative_prompt,
                        "model": model,
                        "steps": steps,
                        "guidance_scale": guidance_scale,
                        "width": width,
                        "height": height,
                        "sampler": sampler,
                        "scheduler": scheduler,
                        "seed": seed,
                        "mufufu_mode": mufufu_mode,
                        "created_at": datetime.now().isoformat()
                    }
                    metadata_path = IMAGES_DIR / f"{gallery_filename}.json"
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)

                    # 自動反省・改善システムで評価（全自動モード）
                    reflection_result = None
                    if AUTO_REFLECTION_AVAILABLE:
                        try:
                            auto_system = get_auto_reflection_system()
                            image_path = str(IMAGES_DIR / gallery_filename)
                            
                            # 評価実行
                            reflection_result = auto_system.process_generated_image(
                                image_path=image_path,
                                prompt=prompt,
                                negative_prompt=negative_prompt,
                                model=model,
                                parameters={
                                    "steps": steps,
                                    "guidance_scale": guidance_scale,
                                    "width": width,
                                    "height": height,
                                    "sampler": sampler,
                                    "scheduler": scheduler,
                                    "seed": seed
                                },
                                auto_improve=True,
                                threshold=0.7
                            )
                            
                            logger.info(f"[自動反省] 総合スコア: {reflection_result['evaluation']['overall_score']:.2f}")
                            
                            # 全自動モード: 改善提案があれば自動的に再生成
                            if reflection_result.get("should_regenerate"):
                                improvement = reflection_result.get("improvement")
                                if improvement:
                                    logger.warning(f"[自動反省] 再生成推奨: {improvement.get('reason', '')}")
                                    logger.info(f"[全自動モード] 改善されたパラメータで自動再生成を開始...")
                                    
                                    # 自動再生成を実行
                                    auto_regenerate(
                                        job_id=job_id,
                                        original_prompt=prompt,
                                        original_negative_prompt=negative_prompt,
                                        original_model=model,
                                        original_parameters={
                                            "steps": steps,
                                            "guidance_scale": guidance_scale,
                                            "width": width,
                                            "height": height,
                                            "sampler": sampler,
                                            "scheduler": scheduler,
                                            "seed": seed
                                        },
                                        improvement=improvement,
                                        original_reflection=reflection_result,
                                        max_retries=2  # 最大2回まで再生成
                                    )
                        except Exception as e:
                            logger.error(f"[自動反省エラー] {e}", exc_info=True)
                    
                    with jobs_lock:
                        if job_id in jobs:
                            jobs[job_id]["status"] = "completed"
                            jobs[job_id]["filename"] = gallery_filename
                            jobs[job_id]["metadata"] = metadata
                            if reflection_result:
                                jobs[job_id]["reflection"] = reflection_result
                                # 改善版ジョブIDは後で設定される（非同期のため）
                else:
                    with jobs_lock:
                        if job_id in jobs:
                            jobs[job_id]["status"] = "failed"
                            jobs[job_id]["error"] = "画像のコピーに失敗しました"
            else:
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "failed"
                        jobs[job_id]["error"] = "画像生成がタイムアウトしました"

        thread = threading.Thread(target=monitor_generation, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "job_id": job_id,
            "prompt_id": prompt_id
        })

    except Exception as e:
        logger.error(f"画像生成エラー: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"エラー詳細: {error_details}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route("/api/job/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """ジョブステータスを取得（改善版ジョブも含む）"""
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({
            "error": "ジョブが見つかりません"
        }), 404
    
    # 改善版ジョブの情報も取得
    response_data = dict(job)
    if "improved_jobs" in job:
        improved_jobs_info = []
        for improved_job_info in job["improved_jobs"]:
            improved_job_id = improved_job_info.get("job_id")
            if improved_job_id and improved_job_id in jobs:
                improved_job = jobs[improved_job_id]
                improved_jobs_info.append({
                    "job_id": improved_job_id,
                    "status": improved_job.get("status"),
                    "filename": improved_job.get("filename"),
                    "score_improvement": improved_job_info.get("score_improvement"),
                    "improved_score": improved_job_info.get("improved_score"),
                    "comparison": improved_job.get("comparison")
                })
        response_data["improved_jobs"] = improved_jobs_info

    return jsonify(response_data)


@app.route("/api/reflection/statistics", methods=["GET"])
def get_reflection_statistics():
    """自動反省・改善システムの統計情報を取得"""
    if not AUTO_REFLECTION_AVAILABLE:
        return jsonify({
            "error": "自動反省・改善システムが利用できません"
        }), 503
    
    try:
        auto_system = get_auto_reflection_system()
        stats = auto_system.get_statistics()
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"統計情報取得エラー: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/api/reflection/evaluate", methods=["POST"])
def evaluate_image():
    """画像を評価（手動）"""
    if not AUTO_REFLECTION_AVAILABLE:
        return jsonify({
            "error": "自動反省・改善システムが利用できません"
        }), 503
    
    try:
        data = request.get_json()
        image_path = data.get("image_path")
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        model = data.get("model", "")
        parameters = data.get("parameters", {})
        
        if not image_path:
            return jsonify({
                "error": "image_pathが必要です"
            }), 400
        
        auto_system = get_auto_reflection_system()
        result = auto_system.process_generated_image(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters,
            auto_improve=data.get("auto_improve", True),
            threshold=data.get("threshold", 0.7)
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        logger.error(f"画像評価エラー: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/images/<filename>", methods=["GET"])
def get_image(filename: str):
    """画像を取得"""
    try:
        image_path = IMAGES_DIR / filename
        if not image_path.exists():
            return jsonify({"error": "画像が見つかりません"}), 404

        return send_from_directory(str(IMAGES_DIR), filename)
    except Exception as e:
        logger.error(f"画像取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/images", methods=["GET"])
def list_images():
    """画像一覧を取得"""
    try:
        images = []
        for image_file in IMAGES_DIR.glob("*.png"):
            image_info = {
                "filename": image_file.name,
                "size": image_file.stat().st_size,
                "created_at": datetime.fromtimestamp(image_file.stat().st_mtime).isoformat()
            }

            # メタデータファイルを読み込む
            metadata_path = IMAGES_DIR / f"{image_file.name}.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        image_info["prompt"] = metadata.get("prompt", "")
                        image_info["original_prompt"] = metadata.get("original_prompt", "")
                        image_info["negative_prompt"] = metadata.get("negative_prompt", "")
                        image_info["model"] = metadata.get("model", "")
                        image_info["seed"] = metadata.get("seed")
                        image_info["steps"] = metadata.get("steps")
                        image_info["guidance_scale"] = metadata.get("guidance_scale")
                except Exception as e:
                    logger.warning(f"メタデータ読み込みエラー ({image_file.name}): {e}")

            images.append(image_info)

        # HTML形式でリクエストされた場合はギャラリーページを返す
        if request.headers.get("Accept", "").find("text/html") >= 0:
            images_sorted = sorted(images, key=lambda x: x['created_at'], reverse=True)
            html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>画像ギャラリー ({len(images)}枚)</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #fff;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            padding: 20px;
        }}
        .image-item {{
            background: #2a2a2a;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s;
        }}
        .image-item:hover {{
            transform: scale(1.05);
        }}
        .image-item img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .image-info {{
            padding: 10px;
            font-size: 12px;
        }}
        .image-info .filename {{
            word-break: break-all;
            margin-bottom: 5px;
        }}
        .image-info .size {{
            color: #888;
        }}
        .image-info .prompt {{
            margin-top: 8px;
            font-size: 11px;
            color: #aaa;
            max-height: 60px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .image-item {{
            cursor: pointer;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }}
        .modal-content {{
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
            margin-top: 50px;
        }}
        .modal-info {{
            color: white;
            padding: 20px;
            text-align: left;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .close {{
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <h1>🎨 画像ギャラリー ({len(images)}枚)</h1>
    <div class="gallery">
"""
            for img in images_sorted:
                prompt_text = img.get('prompt', 'プロンプト情報なし')
                prompt_display = prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text
                html += f"""
        <div class="image-item" onclick="showImage('{img['filename']}', {json.dumps(img, ensure_ascii=False)})">
            <img src="/images/{img['filename']}" alt="{img['filename']}" loading="lazy">
            <div class="image-info">
                <div class="filename">{img['filename'][:50]}...</div>
                <div class="size">{img['size']:,} bytes</div>
                <div class="prompt">{prompt_display}</div>
            </div>
        </div>
"""
            html += """
    </div>

    <div id="imageModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage">
        <div class="modal-info" id="modalInfo"></div>
    </div>

    <script>
        function showImage(filename, info) {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            const modalInfo = document.getElementById('modalInfo');

            modal.style.display = 'block';
            modalImg.src = '/images/' + filename;

            let infoHtml = '<h2>画像情報</h2>';
            infoHtml += '<p><strong>ファイル名:</strong> ' + info.filename + '</p>';
            if (info.prompt) {
                infoHtml += '<p><strong>プロンプト:</strong><br>' + info.prompt.replace(/,/g, ',<br>') + '</p>';
            }
            if (info.original_prompt) {
                infoHtml += '<p><strong>元のプロンプト:</strong><br>' + info.original_prompt.replace(/,/g, ',<br>') + '</p>';
            }
            if (info.negative_prompt) {
                infoHtml += '<p><strong>ネガティブプロンプト:</strong><br>' + info.negative_prompt.replace(/,/g, ',<br>') + '</p>';
            }
            if (info.model) {
                infoHtml += '<p><strong>モデル:</strong> ' + info.model + '</p>';
            }
            if (info.seed !== null && info.seed !== undefined) {
                infoHtml += '<p><strong>Seed:</strong> ' + info.seed + '</p>';
            }
            if (info.steps) {
                infoHtml += '<p><strong>Steps:</strong> ' + info.steps + '</p>';
            }
            if (info.guidance_scale) {
                infoHtml += '<p><strong>CFG Scale:</strong> ' + info.guidance_scale + '</p>';
            }
            infoHtml += '<p><strong>作成日時:</strong> ' + info.created_at + '</p>';
            infoHtml += '<p><strong>サイズ:</strong> ' + info.size.toLocaleString() + ' bytes</p>';

            modalInfo.innerHTML = infoHtml;
        }

        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }

        window.onclick = function(event) {
            const modal = document.getElementById('imageModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    </script>
"""
            html += """
    </div>
</body>
</html>
"""
            return html

        return jsonify({
            "success": True,
            "images": images,
            "count": len(images)
        })
    except Exception as e:
        logger.error(f"画像一覧取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def gallery_index():
    """ギャラリーのトップページ"""
    return list_images()


if __name__ == "__main__":
    logger.info(f"🎨 Gallery API Server 起動中...")
    logger.info(f"   ComfyUI URL: {COMFYUI_URL}")
    logger.info(f"   ポート: {GALLERY_PORT}")
    logger.info(f"   画像ディレクトリ: {IMAGES_DIR}")

    app.run(host="0.0.0.0", port=GALLERY_PORT, debug=True)
