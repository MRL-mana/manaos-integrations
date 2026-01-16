# OCR文字修正ガイド

## モデル選択

### 現在の設定
- **デフォルト**: `qwen2.5:7b`（バランス型、高速）
- **大きなモデル**: 環境変数で自動選択可能

### 大きなモデルを使う方法

#### 方法1: 環境変数で自動選択（推奨）
```powershell
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_ocr_corrector.py input.xlsx output.xlsx
```

#### 方法2: 特定のモデルを指定
```powershell
$env:MANA_OCR_LLM_MODEL="qwen3:30b"
python excel_llm_ocr_corrector.py input.xlsx output.xlsx
```

### 利用可能な大きなモデル（優先順位順）

1. **qwen2.5-72b-instruct:IQ1_M** (72B)
   - 最高精度
   - 処理時間: 長い
   - メモリ: 大量

2. **qwen3:30b** (30B)
   - 高精度
   - 処理時間: 中程度
   - メモリ: 多い

3. **llama3.1:70b** (70B)
   - 高精度
   - 処理時間: 長い
   - メモリ: 大量

4. **qwen2.5:14b** (14B)
   - 中規模
   - 処理時間: 中程度
   - メモリ: 中程度

### 推奨設定

**精度重視（日報データなど）**:
```powershell
$env:MANA_OCR_USE_LARGE_MODEL="1"
```

**速度重視**:
```powershell
# 環境変数を設定しない（デフォルトのqwen2.5:7bを使用）
```

### 注意事項

- 大きなモデルは処理時間が長くなります
- GPUメモリが不足する場合はCPUにフォールバックします
- モデルがインストールされていない場合は自動的にデフォルトにフォールバックします
