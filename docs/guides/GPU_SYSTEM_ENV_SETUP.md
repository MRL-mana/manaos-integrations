# GPU設定 - システム環境変数として設定完了

## 実行した作業

### ✅ 完了した作業

1. **システム環境変数として設定**
   - `OLLAMA_NUM_GPU = 1`
   - `OLLAMA_GPU_LAYERS = 99`
   - `OLLAMA_CUDA = 1`

2. **Ollamaを再起動**
   - 完全に停止
   - セッション環境変数も設定
   - GPUモードで起動

3. **起動確認**
   - Ollama APIが応答することを確認

4. **GPU使用テスト**
   - LLMを呼び出してGPU使用を確認

## 設定内容

### システム環境変数（永続化）

以下の環境変数がシステム環境変数として設定されています：

- `OLLAMA_NUM_GPU = 1` - GPUの数を指定
- `OLLAMA_GPU_LAYERS = 99` - GPUレイヤー数を指定（可能な限りGPUを使用）
- `OLLAMA_CUDA = 1` - CUDAを有効化（Windowsで重要）

### 確認方法

```powershell
# システム環境変数を確認
[System.Environment]::GetEnvironmentVariable("OLLAMA_NUM_GPU", "Machine")
[System.Environment]::GetEnvironmentVariable("OLLAMA_GPU_LAYERS", "Machine")
[System.Environment]::GetEnvironmentVariable("OLLAMA_CUDA", "Machine")
```

## 再起動後の動作

システム環境変数として設定されているため、**PCを再起動しても環境変数は有効**です。

Ollamaを起動すると、自動的にGPUモードで実行されます。

## GPU使用の確認

### 1. `ollama ps`で確認

```powershell
ollama ps
```

- `100% CPU` → CPUモードで実行されている
- `GPU`または`GPU+CPU` → GPUモードで実行されている

### 2. `nvidia-smi`で確認

```powershell
nvidia-smi
```

- GPU使用率が上がっている → GPUが使用されている
- VRAM使用量が増えている → GPUメモリが使用されている

### 3. API呼び出し時に`num_gpu`を指定

```json
{
  "model": "qwen2.5:7b",
  "prompt": "こんにちは",
  "options": {
    "num_gpu": 99
  }
}
```

## ManaOS統合APIサーバーでの動作

`llm_routing.py`では、GPUが利用可能な場合に自動的に`num_gpu: 99`を指定するように設定されています。

```python
if not gpu_in_use:
    request_params["options"] = {
        "num_gpu": 99  # GPUを最大限使用
    }
```

## トラブルシューティング

### GPUが使用されない場合

1. **環境変数が設定されているか確認**
   ```powershell
   [System.Environment]::GetEnvironmentVariable("OLLAMA_NUM_GPU", "Machine")
   [System.Environment]::GetEnvironmentVariable("OLLAMA_GPU_LAYERS", "Machine")
   [System.Environment]::GetEnvironmentVariable("OLLAMA_CUDA", "Machine")
   ```

2. **Ollamaを完全に再起動**
   ```powershell
   Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
   Start-Process ollama
   ```

3. **CUDAがインストールされているか確認**
   ```powershell
   nvidia-smi
   ```

## 注意事項

- システム環境変数として設定するには、管理者権限が必要です
- PCを再起動すると、環境変数は自動的に読み込まれます
- Ollamaを起動すると、自動的にGPUモードで実行されます
- 実際にLLMを呼び出すと、モデルがロードされ、GPU使用率が上がります



