# ComfyUI Dockerfile
# GPU対応の画像生成AIコンテナ

FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ComfyUIをクローン
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /app

# 依存関係のインストール
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r /app/requirements.txt

# モデルディレクトリの作成
RUN mkdir -p /app/models/checkpoints \
    /app/models/vae \
    /app/models/loras \
    /app/models/upscale_models \
    /app/models/controlnet \
    /app/output \
    /app/input \
    /app/custom_nodes \
    /app/logs

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/app

# ポート公開
EXPOSE 8188

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || exit 1

# ComfyUI起動
CMD ["python", "main.py", "--port", "8188", "--listen"]
