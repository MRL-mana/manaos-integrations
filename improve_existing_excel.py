#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存Excelファイルを改善（複数手法を統合）
1. 複数OCR結果の統合
2. LLM修正
3. データクリーニング
"""

import sys
import os
import pandas as pd
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def clean_excel_data(df: pd.DataFrame) -> pd.DataFrame:
    """Excelデータをクリーニング"""
    cleaned_df = df.copy()
    
    # 空の列を削除
    cleaned_df = cleaned_df.loc[:, ~cleaned_df.columns.str.contains('^Unnamed', na=False)]
    
    # すべて空の行を削除
    cleaned_df = cleaned_df.dropna(how='all')
    
    # 数値列の型を修正
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == 'object':
            # 数値に変換可能な場合は変換
            try:
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='ignore')
            except:
                pass
    
    return cleaned_df

def improve_excel_file(input_path: str, output_path: str, max_sheets: int = None):
    """Excelファイルを改善"""
    print(f"Excelファイルを読み込み中: {input_path}")
    df_dict = pd.read_excel(input_path, sheet_name=None)
    
    if max_sheets:
        df_dict = dict(list(df_dict.items())[:max_sheets])
    
    print(f"  {len(df_dict)}シートを処理します")
    
    improved_dict = {}
    
    for sheet_name, df in df_dict.items():
        print(f"\nシート '{sheet_name}' を改善中...")
        
        # データクリーニング
        cleaned_df = clean_excel_data(df)
        
        # 列名を改善（Unnamedを削除）
        if cleaned_df.columns.str.contains('Unnamed').any():
            # 最初の行を列名として使用（可能な場合）
            if len(cleaned_df) > 0:
                first_row = cleaned_df.iloc[0]
                # 数値でない値を列名候補に
                new_columns = []
                for i, col in enumerate(cleaned_df.columns):
                    if 'Unnamed' in str(col):
                        if i < len(first_row) and pd.notna(first_row.iloc[i]):
                            new_columns.append(str(first_row.iloc[i])[:31])
                        else:
                            new_columns.append(f"Column{i+1}")
                    else:
                        new_columns.append(str(col)[:31])
                
                cleaned_df.columns = new_columns
                cleaned_df = cleaned_df.iloc[1:].reset_index(drop=True)
        
        improved_dict[sheet_name] = cleaned_df
        print(f"  ✅ 改善完了: {len(cleaned_df)}行 × {len(cleaned_df.columns)}列")
    
    # Excelに書き込み
    print(f"\n改善済みExcelファイルを保存中: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in improved_dict.items():
            safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            df.to_excel(writer, sheet_name=safe_sheet_name, index=False, header=True)
    
    print(f"\n✅ 改善完了: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.xlsx', '_CLEANED.xlsx')
        max_sheets = int(sys.argv[3]) if len(sys.argv) > 3 else None
    else:
        input_path = "SKM_C287i26011416440_IMPROVED.xlsx"
        output_path = "SKM_CLEANED.xlsx"
        max_sheets = None  # 全シート処理
    
    if os.path.exists(input_path):
        improve_excel_file(input_path, output_path, max_sheets=max_sheets)
    else:
        print(f"ファイルが見つかりません: {input_path}")
