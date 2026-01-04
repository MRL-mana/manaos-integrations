# GPUモード再起動 - 状況まとめ

## 実行した作業

### ✅ 完了した作業
1. Ollamaを完全に停止
2. 環境変数を設定（セッション + ユーザー環境変数として永続化）
   - `OLLAMA_NUM_GPU = 1`
   - `OLLAMA_GPU_LAYERS = 99`
3. OllamaをGPUモードで再起動
4. ManaOS統合APIサーバーを再起動

## 現在の状況

### 環境変数
- ✅ `OLLAMA_NUM_GPU = 1`（設定済み）
- ✅ `OLLAMA_GPU_LAYERS = 99`（設定済み）
- ✅ ユーザー環境変数として永続化済み

### GPU使用状況
- GPU使用率: 4-7%（低い）
- VRAM使用量: 1,324-1,370 MB / 16,303 MB

### Ollamaプロセス
- ✅ Ollamaは起動中
- ⚠️ `ollama ps`でモデルが表示されない（まだロードされていない）

## 問題点

### 1. GPU使用率が低い
- モデルがまだロードされていない可能性
- 実際にLLMを呼び出すとGPU使用率が上がる可能性

### 2. `ollama ps`でモデルが表示されない
- モデルがまだロードされていない
- 実際にLLMを呼び出すとロードされる

## 次のステップ

### 実際にLLMを呼び出して確認

1. **Ollama API直接呼び出し**
   ```powershell
   curl -X POST http://localhost:11434/api/generate `
     -H "Content-Type: application/json" `
     -d '{"model": "qwen2.5:7b", "prompt": "こんにちは", "options": {"num_gpu": 99}, "stream": false}'
   ```

2. **ManaOS統合API経由**
   ```powershell
   curl -X POST http://localhost:9500/api/llm/chat `
     -H "Content-Type: application/json" `
     -d '{"messages": [{"role": "user", "content": "こんにちは"}], "task_type": "conversation"}'
   ```

3. **GPU使用率を確認**
   ```powershell
   nvidia-smi
   ollama ps
   ```

## 注意事項

- 環境変数は新しいプロセスにのみ適用されます
- Ollamaを再起動した後、`ollama ps`でGPUモードになっているか確認してください
- `100% CPU`と表示される場合は、まだCPUモードで実行されています
- `GPU`または`GPU+CPU`と表示される場合は、GPUが使用されています

## トラブルシューティング

### GPUが使用されない場合

1. **Ollamaを完全に停止して再起動**
   ```powershell
   Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
   $env:OLLAMA_NUM_GPU = 1
   $env:OLLAMA_GPU_LAYERS = 99
   Start-Process ollama
   ```

2. **システム環境変数に設定（永続化）**
   - システムのプロパティ → 環境変数
   - `OLLAMA_NUM_GPU` = `1`
   - `OLLAMA_GPU_LAYERS` = `99`

3. **Ollamaの設定ファイルを確認**
   - `%USERPROFILE%\.ollama\config.json`（存在する場合）



