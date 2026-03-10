#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studio修正結果をGoogle Driveにアップロード"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

from google_drive_integration import GoogleDriveIntegration

print("=" * 60)
print("アンサンブル修正結果をGoogle Driveにアップロード")
print("=" * 60)

# Google Drive統合を初期化
drive = GoogleDriveIntegration()

if not drive.is_available():
    print("✗ Google Driveが利用できません")
    print("  認証が必要です")
    sys.exit(1)

# ファイルをアップロード（アンサンブル修正版）
file_path = r"c:\Users\mana4\Desktop\manaos_integrations\SKM_TEST_P1_ENSEMBLE.xlsx"
file_name = "SKM_TEST_P1_ENSEMBLE.xlsx"

print(f"\nファイルをアップロード中: {file_name}")
print(f"  パス: {file_path}")

file_id = drive.upload_file(
    file_path=file_path,
    file_name=file_name,
    overwrite=True
)

if file_id:
    print(f"\n✓ アップロード成功!")
    print(f"  ファイルID: {file_id}")
    print(f"  URL: https://drive.google.com/file/d/{file_id}/view")
else:
    print("\n✗ アップロード失敗")

print("=" * 60)
