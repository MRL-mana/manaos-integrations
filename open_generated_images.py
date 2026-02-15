#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成された画像を開く"""

import os
import subprocess
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")

print("=" * 60)
print("生成された画像を開く")
print("=" * 60)
print()

# 生成された画像ファイル
generated_files = [
    "ComfyUI_00210_.png",
    "ComfyUI_00211_.png",
    "ComfyUI_00212_.png",
    "ComfyUI_00213_.png",
    "ComfyUI_00214_.png",
    "ComfyUI_00215_.png",
    "ComfyUI_00216_.png",
    "ComfyUI_00217_.png",
    "ComfyUI_00218_.png",
    "ComfyUI_00219_.png",
    "ComfyUI_00220_.png",
    "ComfyUI_00221_.png",
    "ComfyUI_00222_.png"
]

print(f"画像ディレクトリ: {COMFYUI_OUTPUT_DIR}")
print()

# 存在するファイルを確認
existing_files = []
for filename in generated_files:
    file_path = COMFYUI_OUTPUT_DIR / filename
    if file_path.exists():
        existing_files.append(file_path)
        print(f"[存在] {filename}")
    else:
        print(f"[未検出] {filename}")

print()
print(f"存在するファイル: {len(existing_files)}件")
print()

if existing_files:
    print("最新の5件の画像を開きます...")
    print()
    
    # 最新の5件を開く
    for i, file_path in enumerate(existing_files[-5:], 1):
        print(f"{i}. {file_path.name}")
        try:
            # Windowsで画像を開く
            os.startfile(str(file_path))
        except Exception as e:
            print(f"   エラー: {e}")
    
    print()
    print("画像を開きました。")
    print()
    print("すべての画像を開く場合は:")
    print(f"  explorer {COMFYUI_OUTPUT_DIR}")
else:
    print("生成された画像が見つかりませんでした。")
    print()
    print("画像ディレクトリを開きます...")
    try:
        os.startfile(str(COMFYUI_OUTPUT_DIR))
    except Exception as e:
        print(f"エラー: {e}")
