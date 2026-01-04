# GPU使用テスト結果

## テスト内容

1. Ollama API直接呼び出し（`num_gpu: 99`を指定）
2. ManaOS統合API経由で呼び出し
3. GPU使用率と`ollama ps`の結果を確認

## 期待される結果

- `ollama ps`で`GPU`または`GPU+CPU`と表示される
- GPU使用率が上がる（10%以上）
- VRAM使用量が増える
- `llm_routing.py`の`cpu_mode`が`False`になる

## 確認ポイント

### 1. `ollama ps`の結果
- `100% CPU` → CPUモードで実行されている
- `GPU`または`GPU+CPU` → GPUモードで実行されている

### 2. GPU使用率
- 低い（5%以下） → CPUモードの可能性
- 高い（10%以上） → GPUモードで実行されている

### 3. VRAM使用量
- 増加している → GPUメモリが使用されている

## トラブルシューティング

### GPUが使用されない場合

1. **Ollamaプロセスを確認**
   ```powershell
   Get-Process ollama
   ```

2. **環境変数を確認**
   ```powershell
   $env:OLLAMA_NUM_GPU
   $env:OLLAMA_GPU_LAYERS
   ```

3. **Ollamaを再起動**
   ```powershell
   Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
   $env:OLLAMA_NUM_GPU = 1
   $env:OLLAMA_GPU_LAYERS = 99
   Start-Process ollama
   ```

4. **システム環境変数に設定（永続化）**
   - システムのプロパティ → 環境変数
   - `OLLAMA_NUM_GPU` = `1`
   - `OLLAMA_GPU_LAYERS` = `99`



