#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sheets集計テスト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_sheets import FileSecretarySheets
from datetime import datetime

def main():
    print("=== Sheets集計テスト ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # Sheets統合初期化
    print("Sheets統合初期化中...")
    sheets = FileSecretarySheets(db)
    
    if not sheets.rows_integration or not sheets.rows_integration.is_available():
        print("⚠️ Rows統合が利用できません")
        print("   設定が必要:")
        print("   - ROWS_API_KEY環境変数")
        print("   - FILE_SECRETARY_SPREADSHEET_ID環境変数（オプション）")
        return
    
    print("✅ Rows統合利用可能\n")
    
    # 週報生成テスト
    print("週報生成テスト:")
    report_data = sheets.generate_weekly_report()
    
    print(f"\n週報データ:")
    print(f"  週開始日: {report_data.get('週開始日')}")
    print(f"  週終了日: {report_data.get('週終了日')}")
    print(f"  新規ファイル数: {report_data.get('新規ファイル数')}")
    print(f"  整理済みファイル数: {report_data.get('整理済みファイル数')}")
    print(f"  PDF数: {report_data.get('PDF数')}")
    print(f"  画像数: {report_data.get('画像数')}")
    print(f"  Excel数: {report_data.get('Excel数')}")
    print(f"  日報タグ数: {report_data.get('日報タグ数')}")
    print(f"  クーポンタグ数: {report_data.get('クーポンタグ数')}")
    
    if 'rows_result' in report_data:
        print(f"\n✅ Rows送信成功")
    elif 'rows_error' in report_data:
        print(f"\n⚠️ Rows送信エラー: {report_data['rows_error']}")
    else:
        print(f"\n⚠️ Rows送信スキップ（spreadsheet_id未設定）")
    
    db.close()

if __name__ == '__main__':
    main()

