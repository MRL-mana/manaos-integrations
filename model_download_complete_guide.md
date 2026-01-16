# 32Bモデルダウンロード完了後の設定

## ダウンロード状況確認

### 自動確認（推奨）
```powershell
python wait_for_lm_studio_model.py qwen2.5-coder-32b-instruct
```

### 手動確認
```powershell
python auto_check_lm_studio_models.py
```

## ダウンロード完了後の自動設定

32Bモデルがダウンロード完了すると、自動的に優先使用されます：

### 現在の設定
- `USE_LM_STUDIO=1` - LM Studioを使用
- `MANA_OCR_USE_LARGE_MODEL=1` - 大きなモデルを優先

### 自動動作
1. 32Bモデルが利用可能になると自動検出
2. 14Bモデルより優先的に使用
3. 複数回修正処理でも自動的に32Bモデルを使用

## 使用方法

### 複数回修正処理（32Bモデル使用）
```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_multi_pass_corrector.py input.xlsx output.xlsx --passes 3
```

### 単回修正処理（32Bモデル使用）
```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_ocr_corrector.py input.xlsx output.xlsx
```

## 期待される効果

### 32Bモデルの利点
- **より高い精度**: OCR修正の精度が向上
- **より正確な文字認識**: 複雑な文字化けも修正可能
- **文脈理解**: より正確な文脈に基づく修正

### 処理時間
- 32Bモデルは14Bモデルより処理時間が長くなる可能性があります
- ただし、精度が大幅に向上します

## 注意事項

- 32Bモデルは約20-25GBのメモリを使用します
- GPUメモリが16GB以上推奨です
- ダウンロード中も14Bモデルで処理は継続可能です
