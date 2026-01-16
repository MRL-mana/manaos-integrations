#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CivitAIお気に入りモデルを選択してダウンロード"""

import sys
import os
from pathlib import Path
import time

# CivitAI統合をインポート
try:
    from civitai_integration import CivitAIIntegration
except ImportError:
    print("❌ civitai_integrationモジュールが見つかりません", file=sys.stderr)
    exit(1)

# ComfyUIモデルディレクトリ
COMFYUI_MODELS_DIR = Path("C:/ComfyUI/models/checkpoints")
COMFYUI_LORA_DIR = Path("C:/ComfyUI/models/loras")

print("=" * 60)
print("CivitAIお気に入りモデル選択ダウンロード")
print("=" * 60)
print()

# APIキーを確認
api_key = os.getenv("CIVITAI_API_KEY")
if not api_key:
    print("⚠️ CIVITAI_API_KEY環境変数が設定されていません")
    exit(1)

# CivitAI統合を初期化
civitai = CivitAIIntegration(api_key=api_key)

if not civitai.is_available():
    print("❌ CivitAI統合が利用できません")
    exit(1)

# お気に入りモデルを取得
print("お気に入りモデルを取得中...")
favorites = civitai.get_favorite_models(limit=100)

if not favorites:
    print("お気に入りモデルが見つかりませんでした。")
    exit(0)

print(f"🌟 お気に入りモデル: {len(favorites)} 件")
print()

# 既存のモデルファイルを確認
existing_checkpoints = set()
if COMFYUI_MODELS_DIR.exists():
    for f in COMFYUI_MODELS_DIR.glob("*.safetensors"):
        existing_checkpoints.add(f.name.lower())
    for f in COMFYUI_MODELS_DIR.glob("*.ckpt"):
        existing_checkpoints.add(f.name.lower())

existing_loras = set()
if COMFYUI_LORA_DIR.exists():
    for f in COMFYUI_LORA_DIR.glob("*.safetensors"):
        existing_loras.add(f.name.lower())
    for f in COMFYUI_LORA_DIR.glob("*.ckpt"):
        existing_loras.add(f.name.lower())

# カテゴリ別に分類
checkpoints_to_download = []
loras_to_download = []

for model in favorites:
    model_type = model.get("type", "")
    model_name = model.get("name", "")
    model_id = model.get("id", "N/A")
    
    # 最新バージョンのファイル名を取得
    versions = model.get("modelVersions", [])
    if versions:
        latest_version = versions[0]
        files = latest_version.get("files", [])
        if files:
            file_name = files[0].get("name", "").lower()
            size_mb = files[0].get("sizeKB", 0) / 1024
            
            # モデルタイプで分類
            if model_type == "Checkpoint":
                if file_name not in existing_checkpoints:
                    checkpoints_to_download.append({
                        "id": model_id,
                        "name": model_name,
                        "file_name": files[0].get("name", ""),
                        "version": latest_version.get("name", ""),
                        "version_id": latest_version.get("id", ""),
                        "size": size_mb
                    })
            elif model_type in ["LORA", "LoCon"]:
                if file_name not in existing_loras:
                    loras_to_download.append({
                        "id": model_id,
                        "name": model_name,
                        "file_name": files[0].get("name", ""),
                        "version": latest_version.get("name", ""),
                        "version_id": latest_version.get("id", ""),
                        "size": size_mb
                    })

# サイズ順にソート（小さいものから）
checkpoints_to_download.sort(key=lambda x: x["size"])
loras_to_download.sort(key=lambda x: x["size"])

print(f"📥 ダウンロード対象:")
print(f"  Checkpoint: {len(checkpoints_to_download)} 件")
print(f"  LoRA: {len(loras_to_download)} 件")
print()

if len(checkpoints_to_download) + len(loras_to_download) == 0:
    print("✅ すべてのモデルがダウンロード済みです！")
    exit(0)

# 小さなモデルから優先（5GB以下）
small_checkpoints = [m for m in checkpoints_to_download if m["size"] <= 5 * 1024]
small_loras = [m for m in loras_to_download if m["size"] <= 5 * 1024]

print("=" * 60)
print("📦 小さなCheckpointモデル（5GB以下）からダウンロード")
print("=" * 60)
print(f"対象: {len(small_checkpoints)} 件")
print()

if small_checkpoints:
    for i, model in enumerate(small_checkpoints, 1):
        print(f"[{i}/{len(small_checkpoints)}] {model['name']}")
        print(f"  サイズ: {model['size']:.1f} MB | ID: {model['id']}")
        
        try:
            download_path = civitai.download_model(
                model_id=model["id"],
                version_id=model["version_id"],
                download_path=str(COMFYUI_MODELS_DIR / model["file_name"])
            )
            
            if download_path:
                print(f"  ✅ ダウンロード完了")
            else:
                print(f"  ❌ ダウンロード失敗")
        except Exception as e:
            print(f"  ❌ エラー: {e}")
        
        print()
        if i < len(small_checkpoints):
            time.sleep(2)

print()
print("=" * 60)
print("🎨 小さなLoRAモデル（5GB以下）からダウンロード")
print("=" * 60)
print(f"対象: {len(small_loras)} 件")
print()

if small_loras:
    for i, model in enumerate(small_loras, 1):
        print(f"[{i}/{len(small_loras)}] {model['name']}")
        print(f"  サイズ: {model['size']:.1f} MB | ID: {model['id']}")
        
        try:
            download_path = civitai.download_model(
                model_id=model["id"],
                version_id=model["version_id"],
                download_path=str(COMFYUI_LORA_DIR / model["file_name"])
            )
            
            if download_path:
                print(f"  ✅ ダウンロード完了")
            else:
                print(f"  ❌ ダウンロード失敗")
        except Exception as e:
            print(f"  ❌ エラー: {e}")
        
        print()
        if i < len(small_loras):
            time.sleep(2)

print()
print("=" * 60)
print("ダウンロード完了（小さなモデルのみ）")
print("=" * 60)
print()
print("大きなモデル（5GB超）は手動でダウンロードしてください。")
print("  python download_favorite_models.py --large-only")
