#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excelファイルを一括改善
- データクリーニング
- LLM修正（オプション）
- Google Driveアップロード
"""

import sys
import os
from improve_existing_excel import improve_excel_file

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

def batch_improve():
    """一括改善"""
    input_file = "SKM_C287i26011416440_IMPROVED.xlsx"
    
    if not os.path.exists(input_file):
        print(f"ファイルが見つかりません: {input_file}")
        return
    
    print("=" * 60)
    print("Excelファイル一括改善")
    print("=" * 60)
    
    # 1. データクリーニング（全シート）
    print("\n[1/3] データクリーニング中...")
    cleaned_file = "SKM_CLEANED_ALL.xlsx"
    improve_excel_file(input_file, cleaned_file, max_sheets=None)
    
    # 2. Google Driveアップロード
    print("\n[2/3] Google Driveにアップロード中...")
    try:
        from google_drive_integration import GoogleDriveIntegration
        drive = GoogleDriveIntegration()
        file_id = drive.upload_file(cleaned_file, file_name=cleaned_file)
        if file_id:
            print(f"  ✅ アップロード完了")
            print(f"  URL: https://drive.google.com/file/d/{file_id}/view")
        else:
            print(f"  ⚠️ アップロード失敗")
    except Exception as e:
        print(f"  ⚠️ アップロードエラー: {e}")
    
    # 3. Google Sheets変換
    print("\n[3/3] Google Sheetsに変換中...")
    try:
        from excel_to_google_sheets import excel_to_google_sheets
        url = excel_to_google_sheets(cleaned_file, "SKM_CLEANED_ALL")
        if url:
            print(f"  ✅ Google Sheets作成完了")
            print(f"  URL: {url}")
    except Exception as e:
        print(f"  ⚠️ Google Sheets変換エラー: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 一括改善完了！")
    print("=" * 60)

if __name__ == "__main__":
    batch_improve()
