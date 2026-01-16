#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI-Managerを一時的に無効化"""

import os
from pathlib import Path

# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
comfyui_path = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
manager_path = comfyui_path / "custom_nodes" / "ComfyUI-Manager"
backup_path = comfyui_path / "custom_nodes" / "ComfyUI-Manager.disabled"

print("=" * 60)
print("ComfyUI-Manager無効化")
print("=" * 60)
print()

if manager_path.exists():
    if backup_path.exists():
        print("既に無効化されています")
    else:
        print("ComfyUI-Managerを無効化中...")
        manager_path.rename(backup_path)
        print("[OK] ComfyUI-Managerを無効化しました")
        print(f"   元に戻すには: {backup_path} を ComfyUI-Manager にリネーム")
else:
    print("ComfyUI-Managerが見つかりません")
    if backup_path.exists():
        print("無効化済みの状態です。")

print()
print("ComfyUIを再起動してください。")
