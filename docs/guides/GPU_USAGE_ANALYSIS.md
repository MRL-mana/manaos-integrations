# GPU使用状況の分析と修正

## 問題の原因

### 1. OllamaがCPUモードで実行されている

`ollama ps`の結果：
```
NAME           ID              SIZE      PROCESSOR    CONTEXT    UNTIL              
llama3.2:3b    a80c4f17acd5    2.5 GB    100% CPU     4096       4 minutes from now    
gpt-oss:20b    17052f91a42e    14 GB     100% CPU     4096       3 minutes from now    
```

**すべてのモデルが`100% CPU`で実行されています。**

### 2. LLMルーティングでGPU使用が明示されていない

- `num_gpu`パラメータが指定されていない
- OllamaはデフォルトでCPUモードになる可能性がある

## 修正内容

### 1. `_call_model`メソッド（generate API用）

```python
# GPUが利用可能な場合はGPUを明示的に使用
if not gpu_in_use:
    options["num_gpu"] = 99  # GPUを最大限使用
    logger.info(f"GPU利用可能: {model}をGPUモードで実行（num_gpu=99）")
```

### 2. `chat`メソッド（chat API用）

```python
# GPUが利用可能な場合はGPUを明示的に使用
if not gpu_in_use:
    request_params["options"] = {
        "num_gpu": 99  # GPUを最大限使用（可能な限りGPUレイヤーを使用）
    }
    logger.info(f"GPUモードで実行: {model} (num_gpu=99)")
```

### 3. GPU使用状況チェックの改善

CPUモードで実行されている場合は、GPUが利用可能と判断するように修正。

## 確認方法

### GPU使用率の確認

```bash
# LLMを呼び出し
curl -X POST http://127.0.0.1:9510/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "こんにちは"}],
    "task_type": "conversation"
  }'

# GPU使用率を確認
nvidia-smi

# Ollamaの状態を確認
ollama ps
```

### 期待される結果

- GPU使用率が大幅に上がる（50%以上）
- VRAM使用量が増加する
- `ollama ps`で`GPU`または`GPU+CPU`と表示される
- 応答速度が向上する

## 追加の対策

### 環境変数の設定

Ollamaを起動する前に環境変数を設定：

```powershell
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
```

### Ollamaの再起動

環境変数を設定した後、Ollamaを再起動：

```powershell
# Ollamaを停止
Stop-Process -Name ollama -Force

# Ollamaを起動（環境変数が設定された状態で）
Start-Process ollama
```

## 注意事項

- `num_gpu: 99`は「可能な限りGPUレイヤーを使用」という意味です
- モデルが小さい場合（3B以下）、GPUを使わない場合があります
- GPUが使用中の場合は自動的にCPUモードに切り替わります




