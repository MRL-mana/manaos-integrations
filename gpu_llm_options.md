# GPU LLM使用オプション

## 選択肢

### 1. WSL2（Linux側）のOllama（推奨）
- **メリット**: GPU完全対応、Ollamaの全機能が使える
- **デメリット**: WSL2の設定が必要

### 2. LM Studio（Windowsネイティブ）
- **メリット**: Windowsで直接動作、GUIで簡単操作
- **デメリット**: OpenAI互換APIのみ

## 推奨: LM Studio（簡単）

LM Studioは既にコードベースに統合されています。

### 使用方法

1. **LM Studioを起動**
   ```powershell
   # LM Studioがインストールされている場合
   Start-Process "C:\Users\mana4\AppData\Local\Programs\LM Studio\LM Studio.exe"
   ```

2. **LM Studioでサーバーを起動**
   - LM Studioの「Server」タブを開く
   - 「Start Server」をクリック
   - ポート: 1234（デフォルト）

3. **環境変数を設定**
   ```powershell
   $env:LLM_SERVER="lm_studio"
   ```

4. **LLM修正を実行**
   ```powershell
   python excel_llm_ocr_corrector.py input.xlsx output.xlsx
   ```

## WSL2（Linux側）のOllama

### 設定方法

1. **WSL2内でOllamaをGPUモードで起動**
   ```powershell
   wsl -d Ubuntu-22.04 -- bash -c "export OLLAMA_NUM_GPU=1; export OLLAMA_GPU_LAYERS=99; nohup ollama serve > /tmp/ollama.log 2>&1 &"
   ```

2. **環境変数を設定**
   ```powershell
   $env:OLLAMA_USE_WSL2="true"
   ```

3. **LLM修正を実行**
   ```powershell
   python excel_llm_ocr_corrector.py input.xlsx output.xlsx
   ```

## どちらを選ぶべきか

- **LM Studio**: 簡単、GUIで操作、Windowsネイティブ
- **WSL2**: より柔軟、Ollamaの全機能、Linux環境
