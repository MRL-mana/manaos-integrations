# Ollama GPU設定 - 最終版

## WindowsでのGPU設定

### 必要な環境変数

1. `OLLAMA_NUM_GPU = 1` - GPUの数を指定
2. `OLLAMA_GPU_LAYERS = 99` - GPUレイヤー数を指定（可能な限りGPUを使用）
3. `OLLAMA_CUDA = 1` - CUDAを有効化（Windowsで重要）

### 設定方法

#### 方法1: PowerShellで設定（セッション用）

```powershell
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
$env:OLLAMA_CUDA = 1
```

#### 方法2: ユーザー環境変数として永続化

```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_LAYERS", "99", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_CUDA", "1", "User")
```

#### 方法3: システム環境変数として設定（推奨）

1. 「設定」→「環境変数を編集」を開く
2. 「新しいシステム変数」を作成
3. 以下の変数を追加：
   - `OLLAMA_NUM_GPU` = `1`
   - `OLLAMA_GPU_LAYERS` = `99`
   - `OLLAMA_CUDA` = `1`

### Ollamaの再起動

環境変数を設定した後、Ollamaを再起動：

```powershell
# Ollamaを停止
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force

# 環境変数を設定
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
$env:OLLAMA_CUDA = 1

# Ollamaを起動
Start-Process ollama
```

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

## ManaOS統合APIサーバーでの設定

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
   $env:OLLAMA_NUM_GPU
   $env:OLLAMA_GPU_LAYERS
   $env:OLLAMA_CUDA
   ```

2. **Ollamaを完全に再起動**
   - タスクマネージャーでOllamaプロセスを終了
   - 環境変数を設定
   - Ollamaを起動

3. **CUDAがインストールされているか確認**
   ```powershell
   nvidia-smi
   ```

4. **システム環境変数に設定（永続化）**
   - 環境変数をシステム環境変数として設定
   - 再起動後も有効

## 注意事項

- 環境変数は新しいプロセスにのみ適用されます
- Ollamaを再起動する前に、必ず環境変数を設定してください
- Windowsでは`OLLAMA_CUDA=1`も設定する必要があります
- システム環境変数として設定すると、再起動後も有効です



