#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナのお気に入りモデル一覧を表示"""

import requests
import json
import sys
import io
from pathlib import Path
import os
from collections import Counter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

COMFYUI_URL = "http://127.0.0.1:8188"

# モデルディレクトリ
COMFYUI_MODELS_DIR = Path(os.getenv("COMFYUI_MODELS_DIR", "C:/ComfyUI/models/checkpoints"))

print("=" * 60)
print("マナのお気に入りモデル一覧")
print("=" * 60)
print()

# 1. ComfyUI APIから利用可能なモデルを取得
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
                    api_models = ckpt_info[0]
                    if isinstance(api_models, list):
                        print(f"✅ ComfyUI APIから {len(api_models)} 件のモデルを検出")
                        print()
                        print("利用可能なモデル一覧:")
                        for i, model in enumerate(api_models, 1):
                            # モデルサイズを確認
                            model_path = COMFYUI_MODELS_DIR / model
                            size_info = ""
                            if model_path.exists():
                                size_mb = model_path.stat().st_size / (1024 * 1024)
                                if size_mb > 1024:
                                    size_info = f" ({size_mb/1024:.1f}GB)"
                                else:
                                    size_info = f" ({size_mb:.1f}MB)"
                            
                            # モデルタイプを判定
                            model_type = ""
                            if "sdxl" in model.lower() or "xl" in model.lower() or "speciosa25D" in model.lower() or "uwazumimix" in model.lower():
                                model_type = " [SDXL]"
                            elif "sd3" in model.lower() or "flux" in model.lower():
                                model_type = " [SD3]"
                            else:
                                model_type = " [SD1.5]"
                            
                            # 問題のあるモデルかチェック
                            problematic = [
                                "0482 dildo masturbation_v1_pony.safetensors",
                                "0687 public indecency_v1_pony.safetensors",
                                "ltx-2-19b-distilled.safetensors",
                                "qqq-BDSM-v3-000010.safetensors",
                                "ZIT_Amateur_Nudes_V2.safetensors",
                                "wan2.2_t2v_highnoise_masturbation_v1.0.safetensors",
                                "waiIllustriousSDXL_v160.safetensors"
                            ]
                            
                            status = ""
                            if model in problematic:
                                status = " ⚠️ 問題あり"
                            
                            print(f"  {i:2d}. {model}{model_type}{size_info}{status}")
                        print()
                        print(f"合計: {len(api_models)} 件")
                        print()
                        
                        # お気に入りモデルの推奨（ファイル名から推測）
                        favorites = []
                        favorite_keywords = [
                            "realisian", "realistic", "real", "beautiful", "perfect",
                            "speciosa", "uwazumimix", "hassaku", "asian"
                        ]
                        
                        for model in api_models:
                            model_lower = model.lower()
                            if any(keyword in model_lower for keyword in favorite_keywords):
                                if model not in problematic:
                                    favorites.append(model)
                        
                        if favorites:
                            print("=" * 60)
                            print("🌟 おすすめモデル（マナ好みのスタイル）")
                            print("=" * 60)
                            for i, model in enumerate(favorites, 1):
                                print(f"  {i}. {model}")
                        else:
                            print("おすすめモデル: すべてのモデルが利用可能です")
                    else:
                        print("⚠️ APIからモデルリストを取得できませんでした")
                else:
                    print("⚠️ APIからモデル情報を取得できませんでした")
            else:
                print("⚠️ APIの構造が予期と異なります")
        else:
            print("⚠️ CheckpointLoaderSimpleが見つかりません")
    else:
        print(f"⚠️ API接続エラー: HTTP {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ ComfyUIに接続できません。ComfyUIが起動しているか確認してください。")
except Exception as e:
    print(f"❌ エラー: {e}")

print()
print("=" * 60)
print("使用方法:")
print("  python generate_20_mana_no_fellatio.py")
print("=" * 60)
