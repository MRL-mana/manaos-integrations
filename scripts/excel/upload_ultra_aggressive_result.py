#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超積極修正結果をGoogle Driveにアップロード"""

import sys
from pathlib import Path

# どのディレクトリから実行しても動くように、リポジトリルートを import パスに追加
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    print("[NG] Google Drive統合が見つかりません")
    sys.exit(1)

print("=" * 60)
print("超積極修正結果をGoogle Driveにアップロード")
print("=" * 60)

drive = GoogleDriveIntegration()

if not drive.is_available():
    print("[NG] Google Driveが利用できません")
    print("  認証が必要な場合は、認証を実行してください")
    sys.exit(1)

target_file = REPO_ROOT / "SKM_TEST_P1_ULTRA_AGGRESSIVE.xlsx"

if not target_file.exists():
    print(f"[NG] ファイルが見つかりません: {target_file}")
    sys.exit(1)

file_size = target_file.stat().st_size
print("\nアップロードするファイル:")
print(f"  [OK] {target_file.name}")
print(f"  サイズ: {file_size:,} bytes ({file_size/1024:.1f}KB)")

print("\n" + "=" * 60)
print("アップロード開始")
print("=" * 60)

try:
    file_id = drive.upload_file(
        file_path=str(target_file),
        folder_id=None,
        file_name=target_file.name,
        overwrite=True,
    )

    if file_id:
        print("\n[OK] アップロード成功")
        print(f"  ファイルID: {file_id}")
        print(f"  Google Drive URL: https://drive.google.com/file/d/{file_id}/view")
        print("\n" + "=" * 60)
        sys.exit(0)

    print("\n[NG] アップロード失敗")
    sys.exit(1)
except Exception as e:
    print(f"\n[NG] エラー: {e}")
    raise

