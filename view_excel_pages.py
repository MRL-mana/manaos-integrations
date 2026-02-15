#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excelファイルの内容を表示（ページ別シート）"""

import pandas as pd
import sys

# UTF-8で出力
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

file_path = 'SKM_C287i26011416440_PAGES.xlsx'

print("=" * 60)
print("Excelファイル内容確認（ページ別シート）")
print("=" * 60)

# シート情報を取得
df_dict = pd.read_excel(file_path, sheet_name=None)

print(f"\nシート数: {len(df_dict)}")
print(f"シート名: {list(df_dict.keys())}")

print("\n各シートの情報:")
for name, sheet in df_dict.items():
    print(f"【{name}】: {len(sheet)}行 × {len(sheet.columns)}列")

# Page1の内容を表示
if 'Page1' in df_dict:
    print("\n" + "=" * 60)
    print("Page1の最初の15行（レイアウト確認）:")
    print("=" * 60)
    page1 = df_dict['Page1']
    for i in range(min(15, len(page1))):
        row_data = []
        for col in page1.columns:
            val = page1.iloc[i][col]
            row_data.append(str(val)[:30] if pd.notna(val) else '')
        print(f"行{i+1}: {' | '.join(row_data)}")

# Page2の内容も表示
if 'Page2' in df_dict:
    print("\n" + "=" * 60)
    print("Page2の最初の10行（レイアウト確認）:")
    print("=" * 60)
    page2 = df_dict['Page2']
    for i in range(min(10, len(page2))):
        row_data = []
        for col in page2.columns:
            val = page2.iloc[i][col]
            row_data.append(str(val)[:30] if pd.notna(val) else '')
        print(f"行{i+1}: {' | '.join(row_data)}")

print("\n" + "=" * 60)
print("完了")
print("=" * 60)
