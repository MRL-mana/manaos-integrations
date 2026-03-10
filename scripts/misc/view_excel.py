#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excelファイルの内容を表示"""

import pandas as pd
import sys

# UTF-8で出力
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

file_path = 'SKM_C287i26011416440_OCR.xlsx'

print("=" * 60)
print("Excelファイル内容確認")
print("=" * 60)

# シート情報を取得
df_dict = pd.read_excel(file_path, sheet_name=None)

print(f"\nシート数: {len(df_dict)}")
print(f"シート名: {list(df_dict.keys())}")

for name, sheet in df_dict.items():
    print(f"\n【{name}】")
    print(f"  行数: {len(sheet)}行")
    print(f"  列数: {len(sheet.columns)}列")
    print(f"  列名: {list(sheet.columns)}")
    
    # 統計情報
    if 'Text' in sheet.columns:
        non_null = sheet['Text'].notna().sum()
        null_count = sheet['Text'].isna().sum()
        print(f"  有効なテキスト行: {non_null}行")
        print(f"  空の行: {null_count}行")

# 最初のシートの内容を表示
first_sheet = list(df_dict.values())[0]
print("\n" + "=" * 60)
print("最初の30行の内容:")
print("=" * 60)

for i in range(min(30, len(first_sheet))):
    text = first_sheet.iloc[i]['Text'] if pd.notna(first_sheet.iloc[i]['Text']) else 'NaN'
    text_str = str(text)[:150] if text != 'NaN' else 'NaN'
    print(f"{i:4d}: {text_str}")

print("\n" + "=" * 60)
print("中間部分（300-310行目）:")
print("=" * 60)

if len(first_sheet) > 300:
    for i in range(300, min(310, len(first_sheet))):
        text = first_sheet.iloc[i]['Text'] if pd.notna(first_sheet.iloc[i]['Text']) else 'NaN'
        text_str = str(text)[:150] if text != 'NaN' else 'NaN'
        print(f"{i:4d}: {text_str}")

print("\n" + "=" * 60)
print("最後の10行:")
print("=" * 60)

for i in range(max(0, len(first_sheet)-10), len(first_sheet)):
    text = first_sheet.iloc[i]['Text'] if pd.notna(first_sheet.iloc[i]['Text']) else 'NaN'
    text_str = str(text)[:150] if text != 'NaN' else 'NaN'
    print(f"{i:4d}: {text_str}")

print("\n" + "=" * 60)
print("完了")
print("=" * 60)
