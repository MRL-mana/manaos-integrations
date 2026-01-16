# LM Studio GPU使用ガイド

## LM Studioの利点

- ✅ **Windowsネイティブ**: WSL2不要
- ✅ **GPU完全対応**: Windowsで直接GPUを使用
- ✅ **GUI操作**: 簡単にモデル選択・サーバー起動
- ✅ **OpenAI互換API**: 既存コードと互換性あり

## 設定方法

### 1. LM Studioでサーバーを起動

1. **LM Studioを起動**
2. **「Server」タブを開く**
3. **「Start Server」をクリック**
4. ポート: 1234（デフォルト）

### 2. 環境変数を設定

```powershell
$env:USE_LM_STUDIO="1"
```

### 3. LLM修正を実行

```powershell
python excel_llm_ocr_corrector.py input.xlsx output.xlsx
```

## 利用可能なモデル

現在利用可能なモデル:
- `qwen2.5-coder-14b-instruct` (14B - 推奨)
- `liquid/lfm2-1.2b` (1.2B - 軽量)
- `openai/gpt-oss-20b` (20B - 高精度)

## GPU使用確認

```powershell
nvidia-smi
# GPU使用率が上がれば、GPUが使用されています
```

## 注意事項

- LM Studioのサーバーが起動している必要があります
- モデルがロードされている必要があります
- GPU使用率が上がれば、GPUが使用されています
