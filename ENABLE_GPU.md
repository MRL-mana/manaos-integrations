# GPU使用を有効化する方法

## 問題

OllamaがCPUモードで実行されており、GPUが使用されていません。

## 解決方法

### 方法1: 環境変数を設定してOllamaを再起動

```powershell
# 環境変数を設定
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99

# Ollamaを再起動
Stop-Process -Name ollama -Force
Start-Process ollama
```

### 方法2: システム環境変数に設定（永続化）

1. システムのプロパティ → 環境変数
2. システム環境変数に追加：
   - `OLLAMA_NUM_GPU` = `1`
   - `OLLAMA_GPU_LAYERS` = `99`
3. Ollamaを再起動

### 方法3: LLMルーティングで明示的に指定（実装済み）

LLMルーティングのコードで`num_gpu: 99`を指定するように修正済みです。

## 確認方法

### GPU使用率の確認

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

# Ollamaの状態を確認
ollama ps
```

### 期待される結果

- GPU使用率が大幅に上がる（50%以上）
- VRAM使用量が増加する
- `ollama ps`で`GPU`または`GPU+CPU`と表示される

## 注意事項

- モデルが小さい場合（3B以下）、GPUを使わない場合があります
- GPUが使用中の場合は自動的にCPUモードに切り替わります
- `num_gpu: 99`は「可能な限りGPUレイヤーを使用」という意味です



