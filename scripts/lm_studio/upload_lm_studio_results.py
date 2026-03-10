#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studio修正結果をGoogle Driveにアップロード"""

import sys
import os
from pathlib import Path

# どのディレクトリから実行しても動くように、リポジトリルートを import パスに追加
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    import io

    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# Google Drive統合をインポート
try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    print("✗ Google Drive統合が見つかりません")
    sys.exit(1)

print("=" * 60)
print("LM Studio修正結果をGoogle Driveにアップロード")
print("=" * 60)

# Google Drive統合を初期化
drive = GoogleDriveIntegration()

if not drive.is_available():
    print("✗ Google Driveが利用できません")
    print("  認証が必要な場合は、認証を実行してください")
    sys.exit(1)

# アップロードするファイル
files_to_upload = [
    ("SKM_TEST_P1_LMSTUDIO.xlsx", "基本的なLLM修正結果"),
    ("SKM_TEST_P1_ENSEMBLE_LMSTUDIO.xlsx", "アンサンブル修正結果"),
    ("SKM_TEST_P1_ULTRA_LMSTUDIO.xlsx", "超強力修正結果（最高精度）"),
]

base_dir = str(REPO_ROOT)

print("\nアップロードするファイル:")
for filename, description in files_to_upload:
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"  ✓ {filename} ({description}) - {size/1024:.1f}KB")
    else:
        print(f"  ✗ {filename} - ファイルが見つかりません")

print("\n" + "=" * 60)
print("アップロード開始")
print("=" * 60)

uploaded_files = []
failed_files = []

for filename, description in files_to_upload:
    filepath = os.path.join(base_dir, filename)

    if not os.path.exists(filepath):
        print(f"\n✗ {filename}: ファイルが見つかりません")
        failed_files.append((filename, "ファイルが見つかりません"))
        continue

    print(f"\n【アップロード中】{filename}")
    print(f"  説明: {description}")

    try:
        # Google Driveにアップロード
        file_id = drive.upload_file(
            file_path=filepath,
            folder_id=None,  # ルートフォルダにアップロード
            file_name=filename,
            overwrite=True,
        )

        if file_id:
            print("  ✓ アップロード成功")
            print(f"  ファイルID: {file_id}")
            print(f"  Google Drive URL: https://drive.google.com/file/d/{file_id}/view")
            uploaded_files.append((filename, file_id))
        else:
            print("  ✗ アップロード失敗")
            failed_files.append((filename, "アップロードに失敗しました"))
    except Exception as e:
        print(f"  ✗ エラー: {e}")
        failed_files.append((filename, str(e)))

print("\n" + "=" * 60)
print("アップロード結果")
print("=" * 60)

if uploaded_files:
    print(f"\n✓ アップロード成功: {len(uploaded_files)}個")
    for filename, file_id in uploaded_files:
        print(f"  - {filename}")
        print(f"    URL: https://drive.google.com/file/d/{file_id}/view")

if failed_files:
    print(f"\n✗ アップロード失敗: {len(failed_files)}個")
    for filename, error in failed_files:
        print(f"  - {filename}: {error}")

print("\n" + "=" * 60)

