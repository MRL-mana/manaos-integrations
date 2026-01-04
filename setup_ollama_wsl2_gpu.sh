#!/bin/bash
# WSL2環境でOllamaをGPUモードで設定するスクリプト

set -e

echo "=== WSL2環境でOllama GPU設定 ==="

# 1. GPU認識確認
echo ""
echo "[1] GPU認識確認中..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    echo "  [OK] GPUが認識されています"
else
    echo "  [ERROR] nvidia-smiが見つかりません"
    echo "  WSL2でGPUを使用するには、Windows側でNVIDIAドライバーをインストールする必要があります"
    exit 1
fi

# 2. CUDA確認
echo ""
echo "[2] CUDA確認中..."
if command -v nvcc &> /dev/null; then
    nvcc --version
    echo "  [OK] CUDAがインストールされています"
else
    echo "  [INFO] CUDAコンパイラは見つかりませんが、Ollamaは動作します"
fi

# 3. Ollamaインストール確認
echo ""
echo "[3] Ollamaインストール確認中..."
if command -v ollama &> /dev/null; then
    echo "  [OK] Ollamaは既にインストールされています"
    ollama --version
else
    echo "  [INFO] Ollamaをインストールします..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 4. 環境変数の設定
echo ""
echo "[4] 環境変数を設定中..."
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_LAYERS=99
export OLLAMA_USE_CUDA=1
export OLLAMA_CUDA=1
export CUDA_VISIBLE_DEVICES=0

# ~/.bashrcに追加（永続化）
if ! grep -q "OLLAMA_NUM_GPU" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Ollama GPU設定" >> ~/.bashrc
    echo "export OLLAMA_NUM_GPU=1" >> ~/.bashrc
    echo "export OLLAMA_GPU_LAYERS=99" >> ~/.bashrc
    echo "export OLLAMA_USE_CUDA=1" >> ~/.bashrc
    echo "export OLLAMA_CUDA=1" >> ~/.bashrc
    echo "export CUDA_VISIBLE_DEVICES=0" >> ~/.bashrc
    echo "  [OK] 環境変数を~/.bashrcに追加しました"
else
    echo "  [INFO] 環境変数は既に設定されています"
fi

# 5. Ollamaを停止（実行中の場合）
echo ""
echo "[5] Ollamaを停止中..."
pkill ollama || true
sleep 2

# 6. Ollamaを起動
echo ""
echo "[6] OllamaをGPUモードで起動中..."
ollama serve &
sleep 5

# 7. 起動確認
echo ""
echo "[7] 起動確認中..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "  [OK] Ollamaが正常に起動しました"
else
    echo "  [WARN] Ollamaの起動確認に失敗しました"
fi

# 8. GPU使用状況確認
echo ""
echo "[8] GPU使用状況確認中..."
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader

# 9. モデルをロードしてテスト
echo ""
echo "[9] モデルをロードしてGPU使用を確認中..."
if ollama list | grep -q "qwen3:4b"; then
    echo "  qwen3:4bモデルが見つかりました"
    echo "  テスト実行中..."
    timeout 10 ollama run qwen3:4b "テスト" || true
    sleep 2
    echo ""
    echo "  ollama psの結果:"
    ollama ps
else
    echo "  [INFO] qwen3:4bモデルが見つかりませんでした"
    echo "  モデルをプルしますか？ (y/n)"
fi

echo ""
echo "=== 設定完了 ==="
echo ""
echo "使用方法:"
echo "  1. WSL2内で: ollama serve"
echo "  2. 別のターミナルで: ollama run <モデル名>"
echo "  3. GPU使用確認: ollama ps"
echo ""

