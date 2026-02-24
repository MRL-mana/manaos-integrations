#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cドライブの重複comfyuiを削除してシンボリックリンクを作成
"""

import os
import shutil
from pathlib import Path

# パス
c_comfyui = Path("C:/Users/mana4/Desktop/manaos_integrations/comfyui")
d_comfyui = Path("D:/manaos_integrations/comfyui")

print("=" * 70)
print("ComfyUI重複削除とシンボリックリンク作成")
print("=" * 70)
print()

# Dドライブのcomfyuiの確認
if not d_comfyui.exists():
    print("[ERROR] Dドライブのcomfyuiが見つかりません")
    exit(1)

print(f"[OK] Dドライブのcomfyuiが存在します: {d_comfyui}")
print()

# Cドライブのcomfyuiの確認
if not c_comfyui.exists():
    print("[INFO] Cドライブのcomfyuiは既に存在しません")
    print("シンボリックリンクを作成します...")
    try:
        os.symlink(str(d_comfyui), str(c_comfyui), target_is_directory=True)
        print("[OK] シンボリックリンク作成成功")
    except OSError as e:
        print(f"[ERROR] シンボリックリンク作成失敗: {e}")
        print("管理者権限でPowerShellを開いて、以下のコマンドを実行してください:")
        print(f'  mklink /D "{c_comfyui}" "{d_comfyui}"')
    exit(0)

# 既にシンボリックリンクかチェック
try:
    if c_comfyui.is_symlink():
        print("[INFO] 既にシンボリックリンクです")
        exit(0)
except Exception:
    pass

# Cドライブのcomfyuiのサイズを確認
print("Cドライブのcomfyuiを確認中...")
total_size = 0
file_count = 0
for file_path in c_comfyui.rglob("*"):
    if file_path.is_file():
        try:
            total_size += file_path.stat().st_size
            file_count += 1
        except Exception:
            pass

print(f"Cドライブのcomfyuiサイズ: {total_size/1024/1024/1024:.2f} GB ({file_count}ファイル)")
print()

# 削除確認
print("Cドライブのcomfyuiを削除してシンボリックリンクを作成します...")
print("（Dドライブのcomfyuiは保持されます）")
print()

try:
    # 削除
    print("削除中...")
    shutil.rmtree(str(c_comfyui))
    print("[OK] 削除完了")
    print()

    # シンボリックリンク作成
    print("シンボリックリンク作成中...")
    try:
        os.symlink(str(d_comfyui), str(c_comfyui), target_is_directory=True)
        print("[OK] シンボリックリンク作成成功")
        print()
        print(f"解放された容量: {total_size/1024/1024/1024:.2f} GB")
    except OSError as e:
        print(f"[ERROR] シンボリックリンク作成失敗: {e}")
        print("管理者権限でPowerShellを開いて、以下のコマンドを実行してください:")
        print(f'  mklink /D "{c_comfyui}" "{d_comfyui}"')
        print()
        print("注意: comfyuiは削除されましたが、シンボリックリンクが作成されていません")
        print("上記のコマンドを実行してシンボリックリンクを作成してください")
except Exception as e:
    print(f"[ERROR] 削除失敗: {e}")
    exit(1)

print()
print("=" * 70)
print("完了")
print("=" * 70)
