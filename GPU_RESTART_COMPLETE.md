# GPUモード再起動完了

## 実行した作業

### 1. OllamaをGPUモードで再起動
- ✅ Ollamaを停止
- ✅ 環境変数を設定: `OLLAMA_NUM_GPU=1`, `OLLAMA_GPU_LAYERS=99`
- ✅ OllamaをGPUモードで起動

### 2. ManaOS統合APIサーバーを再起動
- ✅ 統合APIサーバーを停止
- ✅ 環境変数を設定して再起動
- ✅ GPUモードで実行される設定

## 確認結果

### GPU使用状況
- GPU使用率: 7%（まだ低い）
- VRAM使用量: 1,332 MB / 16,303 MB

### LLMルーティング
- CPUモード: False（GPUモードで実行される設定）
- `num_gpu: 99`を指定するように修正済み

## 次のステップ

### GPU使用を確認する方法

1. **実際にLLMを呼び出す**
   ```bash
   curl -X POST http://localhost:9500/api/llm/chat \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [{"role": "user", "content": "こんにちは"}],
       "task_type": "conversation"
     }'
   ```

2. **GPU使用率を監視**
   ```bash
   nvidia-smi
   ```

3. **Ollamaの状態を確認**
   ```bash
   ollama ps
   ```

## 注意事項

- GPU使用率が低い場合、モデルが小さいか、まだロードされていない可能性があります
- 大きなモデル（7B以上）を使用すると、GPU使用率が上がります
- `ollama ps`で`GPU`または`GPU+CPU`と表示されれば、GPUが使用されています

## トラブルシューティング

### GPUが使用されない場合

1. **環境変数が設定されているか確認**
   ```powershell
   $env:OLLAMA_NUM_GPU
   $env:OLLAMA_GPU_LAYERS
   ```

2. **Ollamaを再起動**
   ```powershell
   Stop-Process -Name ollama -Force
   Start-Process ollama
   ```

3. **システム環境変数に設定（永続化）**
   - システムのプロパティ → 環境変数
   - `OLLAMA_NUM_GPU` = `1`
   - `OLLAMA_GPU_LAYERS` = `99`



