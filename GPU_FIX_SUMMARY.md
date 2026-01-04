# GPU使用問題の修正

## 問題

GPUが全然使われていない問題を修正しました。

## 原因

1. **OllamaがCPUモードで実行されていた**
   - `ollama ps`で`100% CPU`と表示
   - `num_gpu`パラメータが指定されていなかった

2. **LLMルーティングでGPU使用が明示されていなかった**
   - GPUが利用可能でも、`num_gpu`を指定しないとCPUモードになる可能性がある

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

## 動作確認

修正後、以下のコマンドでGPU使用を確認できます：

```bash
# LLMを呼び出し
curl -X POST http://localhost:9500/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "こんにちは"}],
    "task_type": "conversation"
  }'

# GPU使用率を確認
nvidia-smi
```

## 期待される動作

- GPU使用率が大幅に上がる（50%以上）
- VRAM使用量が増加する
- 応答速度が向上する（GPU使用時）

## 注意事項

- `num_gpu: 99`は「可能な限りGPUレイヤーを使用」という意味です
- GPUが使用中の場合は自動的にCPUモードに切り替わります
- サーバーを再起動すると修正が反映されます



