#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel Vision LLM修正の簡単なテスト
最初のシートだけ処理
"""

import sys
import os
import pytest

# openpyxl 未インストール時はスキップ
pytest.importorskip("openpyxl")

import pandas as pd

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

def test_excel_vision_simple():
    """最初のシートだけ処理"""
    excel_path = "SKM_C287i26011416440_IMPROVED.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"エラー: Excelファイルが見つかりません: {excel_path}")
        return
    
    print(f"Excelファイルを読み込み中: {excel_path}")
    df_dict = pd.read_excel(excel_path, sheet_name=None)
    
    if not df_dict:
        print("エラー: シートが見つかりません")
        return
    
    # 最初のシートだけ処理
    first_sheet_name = list(df_dict.keys())[0]
    df = df_dict[first_sheet_name]
    
    print(f"\nシート '{first_sheet_name}' を処理中...")
    print(f"  サイズ: {len(df)}行 × {len(df.columns)}列")
    
    # サンプルデータを表示
    print(f"\n最初の5行のサンプル:")
    print(df.head(5).to_string())
    
    print(f"\n✅ テスト完了！")
    print(f"  このシートをVision LLMで修正するには、excel_vision_llm_corrector.pyを使用してください")
    print(f"  コマンド: python excel_vision_llm_corrector.py \"{excel_path}\" \"output.xlsx\" 1")

if __name__ == "__main__":
    test_excel_vision_simple()
