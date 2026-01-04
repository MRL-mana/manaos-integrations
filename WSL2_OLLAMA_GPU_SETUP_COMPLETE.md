# WSL2環境でのOllama GPU設定完了

## 設定完了日時
2026年1月3日

## 設定内容

### 1. WSL2環境の確認
- ✅ WSL2がインストール済み（Ubuntu-22.04）
- ✅ GPUがWSL2内で認識されている（RTX 5080）
- ✅ OllamaがWSL2内にインストール済み（0.13.5）

### 2. 環境変数の設定
以下の環境変数を`~/.bashrc`に追加しました：
```bash
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_LAYERS=99
export OLLAMA_USE_CUDA=1
export OLLAMA_CUDA=1
export CUDA_VISIBLE_DEVICES=0
```

### 3. 起動スクリプト
`start_ollama_wsl2_gpu.ps1`を作成しました。このスクリプトでWSL2環境でOllamaをGPUモードで起動できます。

## 使用方法

### Ollamaを起動
```powershell
cd c:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_ollama_wsl2_gpu.ps1
```

### モデルを実行
```powershell
# WSL2内でモデルを実行
wsl -d Ubuntu-22.04 -- ollama run qwen3:4b "プロンプト"

# または環境変数を設定して実行
wsl -d Ubuntu-22.04 -- bash -c "export OLLAMA_NUM_GPU=1; export OLLAMA_GPU_LAYERS=99; export OLLAMA_USE_CUDA=1; export OLLAMA_CUDA=1; export CUDA_VISIBLE_DEVICES=0; ollama run qwen3:4b 'プロンプト'"
```

### GPU使用状況を確認
```powershell
# ollama psで確認
wsl -d Ubuntu-22.04 -- ollama ps

# nvidia-smiで確認
wsl -d Ubuntu-22.04 -- nvidia-smi
```

### Ollamaを停止
```powershell
wsl -d Ubuntu-22.04 -- pkill ollama
```

## 注意事項

1. **モデルのダウンロード**: 初回実行時はモデルのダウンロードに時間がかかります。
2. **環境変数**: WSL2内で実行する際は、環境変数を設定する必要があります。
3. **ポート**: WSL2内のOllamaは`localhost:11434`でアクセスできます。

## 次のステップ

1. モデルのダウンロード完了を待つ
2. モデルを実行してGPU使用を確認
3. `ollama ps`で`PROCESSOR: GPU`と表示されることを確認

## トラブルシューティング

### GPUが使用されない場合
1. 環境変数が正しく設定されているか確認
2. WSL2内で`nvidia-smi`が動作するか確認
3. Ollamaを再起動

### ログの確認
```powershell
wsl -d Ubuntu-22.04 -- cat /tmp/ollama.log
```

