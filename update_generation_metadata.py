#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成メタデータを更新して、実際の出力ファイル名を紐付けるスクリプト"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path
from datetime import datetime, timedelta
import requests

GENERATION_METADATA_DB = Path("C:/ComfyUI/input/mana_favorites/generation_metadata.json")
COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")
COMFYUI_URL = "http://127.0.0.1:8188"

print("=" * 60)
print("生成メタデータ更新（出力ファイル名の紐付け）")
print("=" * 60)
print()

# 生成メタデータを読み込み
if not GENERATION_METADATA_DB.exists():
    print("⚠️ 生成メタデータが見つかりません")
    sys.exit(1)

try:
    with open(GENERATION_METADATA_DB, 'r', encoding='utf-8') as f:
        generation_metadata = json.load(f)
except Exception as e:
    print(f"⚠️ メタデータの読み込みエラー: {e}")
    sys.exit(1)

print(f"生成メタデータ: {len(generation_metadata)}件")
print()

def _extract_output_images_from_history(history_json, prompt_id):
    try:
        item = history_json.get(prompt_id) if isinstance(history_json, dict) else None
        if not isinstance(item, dict):
            return []
        outputs = item.get("outputs", {})
        if not isinstance(outputs, dict):
            return []

        images = []
        for out in outputs.values():
            if not isinstance(out, dict):
                continue
            for img in out.get("images", []) or []:
                if not isinstance(img, dict):
                    continue
                if img.get("type") == "output" and img.get("filename"):
                    images.append(img)
        return images
    except Exception:
        return []

def get_output_filenames_from_history(prompt_id):
    """ComfyUI /history/{prompt_id} から出力ファイル名を取得（取得できなければ空）"""
    try:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        if r.status_code != 200:
            return [], []
        imgs = _extract_output_images_from_history(r.json(), prompt_id)
        if not imgs:
            return [], []
        filenames = []
        paths = []
        for img in imgs:
            subfolder = img.get("subfolder") or ""
            filename = img.get("filename")
            filenames.append(filename)
            if subfolder:
                paths.append(str(COMFYUI_OUTPUT_DIR / subfolder / filename))
            else:
                paths.append(str(COMFYUI_OUTPUT_DIR / filename))
        return filenames, paths
    except Exception:
        return [], []

# メタデータを更新
updated_count = 0
history_updated = 0
fallback_updated = 0
for gen_id, gen_data in generation_metadata.items():
    output_filename = gen_data.get("output_filename", "")
    generated_at_str = gen_data.get("generated_at", "")
    prompt_id = str(gen_data.get("prompt_id", "")).strip()
    
    # 1) prompt_id があれば /history から実名を優先取得
    if prompt_id:
        filenames, paths = get_output_filenames_from_history(prompt_id)
        if filenames:
            gen_data["output_filenames"] = filenames
            gen_data["output_paths"] = paths
            gen_data["output_filename"] = filenames[0]
            gen_data["output_path"] = paths[0] if paths else str(COMFYUI_OUTPUT_DIR / filenames[0])
            gen_data["output_filename_is_estimated"] = False
            updated_count += 1
            history_updated += 1
            continue
    
    # 2) フォールバック: 生成時刻から近い画像を推測（精度は低い）
    if not COMFYUI_OUTPUT_DIR.exists():
        continue
    if generated_at_str:
        try:
            gen_time = datetime.strptime(generated_at_str, "%Y-%m-%d %H:%M:%S")
            # 生成時刻の前後30分以内の画像を探す
            time_window_start = gen_time - timedelta(minutes=30)
            time_window_end = gen_time + timedelta(minutes=30)
            
            # 直近24時間だけ見る（重くしない）
            cutoff_time = datetime.now() - timedelta(hours=24)
            candidates = []
            for img_file in COMFYUI_OUTPUT_DIR.glob("ComfyUI_*.png"):
                try:
                    mod_time = datetime.fromtimestamp(img_file.stat().st_mtime)
                    if mod_time > cutoff_time and time_window_start <= mod_time <= time_window_end:
                        candidates.append((mod_time, img_file))
                except:
                    pass
            if candidates:
                candidates.sort(key=lambda x: x[0])
                chosen = candidates[0][1]
                gen_data["output_filename"] = chosen.name
                gen_data["output_path"] = str(chosen)
                gen_data["output_filename_is_estimated"] = True
                updated_count += 1
                fallback_updated += 1
        except:
            pass

# 更新されたメタデータを保存
if updated_count > 0:
    try:
        with open(GENERATION_METADATA_DB, 'w', encoding='utf-8') as f:
            json.dump(generation_metadata, f, ensure_ascii=False, indent=2)
        print(f"✅ {updated_count}件のメタデータを更新しました")
        print(f"  - /history から更新: {history_updated}件")
        print(f"  - 時刻推測で更新: {fallback_updated}件")
    except Exception as e:
        print(f"⚠️ メタデータの保存エラー: {e}")
else:
    print("ℹ️ 更新が必要なメタデータはありませんでした")

print()
print("=" * 60)
print("完了")
print("=" * 60)
