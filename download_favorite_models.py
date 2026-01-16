#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CivitAIお気に入りモデルを自動ダウンロード"""

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
print("CivitAIお気に入りモデル自動ダウンロード")
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

# 既存のモデルファイルを確認（複数ディレクトリから検索）
print("既存のモデルファイルを検索中...")
existing_checkpoints = set()
existing_loras = set()

# 検索対象ディレクトリ
search_dirs = [
    COMFYUI_MODELS_DIR,
    Path("C:/mana_workspace/models"),
    Path.home() / "Downloads",
    Path("C:/models"),
    Path("D:/models"),
    Path("C:/StableDiffusion/models"),
    Path("C:/AI/models"),
]

for search_dir in search_dirs:
    if search_dir.exists():
        for f in search_dir.rglob("*.safetensors"):
            if "lora" in f.parent.name.lower() or "lora" in f.name.lower():
                existing_loras.add(f.name.lower())
            else:
                existing_checkpoints.add(f.name.lower())
        for f in search_dir.rglob("*.ckpt"):
            if "lora" in f.parent.name.lower() or "lora" in f.name.lower():
                existing_loras.add(f.name.lower())
            else:
                existing_checkpoints.add(f.name.lower())

print(f"  既存Checkpoint: {len(existing_checkpoints)} 件")
print(f"  既存LoRA: {len(existing_loras)} 件")
print()

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
            
            # モデルタイプで分類
            if model_type == "Checkpoint":
                if file_name not in existing_checkpoints:
                    checkpoints_to_download.append({
                        "id": model_id,
                        "name": model_name,
                        "file_name": files[0].get("name", ""),
                        "version": latest_version.get("name", ""),
                        "version_id": latest_version.get("id", ""),
                        "size": files[0].get("sizeKB", 0) / 1024  # MB
                    })
            elif model_type in ["LORA", "LoCon"]:
                if file_name not in existing_loras:
                    loras_to_download.append({
                        "id": model_id,
                        "name": model_name,
                        "file_name": files[0].get("name", ""),
                        "version": latest_version.get("name", ""),
                        "version_id": latest_version.get("id", ""),
                        "size": files[0].get("sizeKB", 0) / 1024  # MB
                    })

print(f"📥 ダウンロード対象:")
print(f"  Checkpoint: {len(checkpoints_to_download)} 件")
print(f"  LoRA: {len(loras_to_download)} 件")
print()

# サイズを計算
total_size_mb = sum(m["size"] for m in checkpoints_to_download + loras_to_download)
total_size_gb = total_size_mb / 1024

if total_size_gb > 1:
    print(f"📊 合計サイズ: {total_size_gb:.2f} GB")
else:
    print(f"📊 合計サイズ: {total_size_mb:.2f} MB")
print()

# 確認
if len(checkpoints_to_download) + len(loras_to_download) == 0:
    print("✅ すべてのモデルがダウンロード済みです！")
    exit(0)

# バッチモード（自動実行）の場合は確認をスキップ
auto_mode = "--auto" in sys.argv or "-y" in sys.argv

if not auto_mode:
    try:
        response = input("ダウンロードを開始しますか？ (Y/N): ")
        if response.upper() != "Y":
            print("ダウンロードをキャンセルしました。")
            exit(0)
    except (EOFError, KeyboardInterrupt):
        print("\nダウンロードをキャンセルしました。")
        exit(0)
else:
    print("自動モード: ダウンロードを開始します...")

print()
print("=" * 60)
print("ダウンロード開始")
print("=" * 60)
print()

# Checkpointをダウンロード
success_count = 0
error_count = 0

if checkpoints_to_download:
    print(f"📦 Checkpointモデル ({len(checkpoints_to_download)} 件)")
    print()
    for i, model in enumerate(checkpoints_to_download, 1):
        print(f"[{i}/{len(checkpoints_to_download)}] {model['name']}")
        print(f"  サイズ: {model['size']:.1f} MB | ID: {model['id']}")
        
        try:
            download_path = civitai.download_model(
                model_id=model["id"],
                version_id=model["version_id"],
                download_path=str(COMFYUI_MODELS_DIR / model["file_name"])
            )
            
            if download_path:
                print(f"  ✅ ダウンロード完了: {model['file_name']}")
                success_count += 1
            else:
                print(f"  ❌ ダウンロード失敗")
                error_count += 1
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            error_count += 1
        
        print()
        
        # レート制限を避けるため少し待機
        if i < len(checkpoints_to_download):
            time.sleep(2)

# LoRAをダウンロード
if loras_to_download:
    print(f"🎨 LoRAモデル ({len(loras_to_download)} 件)")
    print()
    for i, model in enumerate(loras_to_download, 1):
        print(f"[{i}/{len(loras_to_download)}] {model['name']}")
        print(f"  サイズ: {model['size']:.1f} MB | ID: {model['id']}")
        
        try:
            download_path = civitai.download_model(
                model_id=model["id"],
                version_id=model["version_id"],
                download_path=str(COMFYUI_LORA_DIR / model["file_name"])
            )
            
            if download_path:
                print(f"  ✅ ダウンロード完了: {model['file_name']}")
                success_count += 1
            else:
                print(f"  ❌ ダウンロード失敗")
                error_count += 1
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            error_count += 1
        
        print()
        
        # レート制限を避けるため少し待機
        if i < len(loras_to_download):
            time.sleep(2)

print()
print("=" * 60)
print("ダウンロード完了")
print("=" * 60)
print(f"✅ 成功: {success_count} 件")
print(f"❌ 失敗: {error_count} 件")
print()
print("ダウンロードしたモデルはComfyUIで使用できます。")
print("  python generate_20_mana_no_fellatio.py")
