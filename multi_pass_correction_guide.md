# 複数回修正処理ガイド

## 概要

OCR結果の精度を向上させるため、複数回の修正処理を自動的に実行します。
各パスで前回の修正結果をさらに改善していきます。

## 使用方法

### 基本的な使い方

```powershell
# 環境変数を設定
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"

# 3回の修正処理を実行
python excel_llm_multi_pass_corrector.py input.xlsx output.xlsx --passes 3
```

### オプション

- `--passes N`: 修正回数を指定（デフォルト: 3回）
- `--verbose`: 詳細な進捗情報を表示

### 例

```powershell
# 5回の修正処理を実行
python excel_llm_multi_pass_corrector.py input.xlsx output.xlsx --passes 5 --verbose
```

## 処理フロー

1. **パス1**: 元のファイルを修正 → `output_pass1.xlsx`
2. **パス2**: パス1の結果をさらに修正 → `output_pass2.xlsx`
3. **パス3**: パス2の結果をさらに修正 → `output.xlsx`（最終ファイル）

## 期待される効果

- **1回目**: 明らかな誤認識を修正
- **2回目**: 残った誤認識をさらに修正
- **3回目**: 細かい誤認識を最終調整

## 注意事項

- 処理時間は修正回数に比例して長くなります
- 中間ファイルは自動的に削除されます
- GPUメモリが不足する場合は、修正回数を減らしてください
