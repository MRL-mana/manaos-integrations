#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→Excel変換完了後の自動処理パイプライン
1. LLM修正を適用
2. Google Sheetsにアップロード
"""

import sys
import os
import time
from pathlib import Path

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def wait_for_file(file_path: str, timeout: int = 3600, check_interval: int = 10):
    """ファイルが作成されるまで待機"""
    file = Path(file_path)
    start_time = time.time()
    
    print(f"ファイルの作成を待機中: {file_path}")
    print(f"タイムアウト: {timeout}秒、チェック間隔: {check_interval}秒")
    
    while time.time() - start_time < timeout:
        if file.exists() and file.stat().st_size > 0:
            # ファイルが存在し、サイズが0より大きい
            # さらに数秒待ってファイルがロックされていないか確認
            time.sleep(2)
            try:
                # ファイルを開いてみる（ロックチェック）
                with open(file, 'rb') as f:
                    f.read(1)
                print(f"✓ ファイルが準備できました: {file_path} ({file.stat().st_size / 1024 / 1024:.2f} MB)")
                return True
            except (PermissionError, IOError):
                # まだロックされている
                print(f"ファイルがロック中... 再試行します...")
                time.sleep(check_interval)
                continue
        else:
            elapsed = int(time.time() - start_time)
            print(f"待機中... ({elapsed}秒経過)")
            time.sleep(check_interval)
    
    print(f"✗ タイムアウト: ファイルが作成されませんでした: {file_path}")
    return False

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python process_complete_pipeline.py <Excelファイルパス>")
        print("例: python process_complete_pipeline.py SKM_ALL_PAGES.xlsx")
        sys.exit(1)
    
    excel_path = Path(sys.argv[1])
    if not excel_path.is_absolute():
        excel_path = Path.cwd() / excel_path
    
    print("=" * 60)
    print("PDF→Excel変換完了後の自動処理パイプライン")
    print("=" * 60)
    print(f"対象ファイル: {excel_path}")
    print()
    
    # ステップ1: ファイルの準備を待つ
    if not excel_path.exists():
        print("ステップ1: ファイルの作成を待機...")
        if not wait_for_file(str(excel_path), timeout=3600, check_interval=10):
            print("✗ ファイルが作成されませんでした。処理を終了します。")
            sys.exit(1)
    else:
        print(f"✓ ファイルが存在します: {excel_path} ({excel_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    print()
    
    # ステップ2: LLM修正を適用
    corrected_path = excel_path.parent / f"{excel_path.stem}_CORRECTED.xlsx"
    print("ステップ2: LLM修正を適用...")
    print(f"  入力: {excel_path}")
    print(f"  出力: {corrected_path}")
    
    try:
        from excel_llm_ocr_corrector import ExcelLLMOCRCorrector
        
        corrector = ExcelLLMOCRCorrector()
        result = corrector.correct_excel(str(excel_path), str(corrected_path), verbose=True)
        
        if result:
            print(f"✓ LLM修正が完了しました: {corrected_path}")
            # 修正版を使用
            final_excel = corrected_path
        else:
            print("⚠ LLM修正に失敗しました。元のファイルを使用します。")
            final_excel = excel_path
    except Exception as e:
        print(f"⚠ LLM修正エラー: {e}")
        print("元のファイルを使用します。")
        final_excel = excel_path
    
    print()
    
    # ステップ3: Google Sheetsにアップロード
    print("ステップ3: Google Sheetsにアップロード...")
    try:
        from excel_to_google_sheets import excel_to_google_sheets
        
        spreadsheet_title = f"{excel_path.stem}_GoogleSheets"
        sheets_url = excel_to_google_sheets(str(final_excel), spreadsheet_title)
        
        if sheets_url:
            print(f"✓ Google Sheetsにアップロード完了:")
            print(f"  {sheets_url}")
        else:
            print("⚠ Google Sheetsへのアップロードに失敗しました。")
    except Exception as e:
        print(f"⚠ Google Sheetsアップロードエラー: {e}")
    
    print()
    print("=" * 60)
    print("処理完了")
    print("=" * 60)

if __name__ == "__main__":
    main()
