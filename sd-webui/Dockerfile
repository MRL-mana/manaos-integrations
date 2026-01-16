# Stable Diffusion WebUI Dockerfile
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

# Stable Diffusion WebUIをクローン
RUN git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git /app

# 依存関係のインストール
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# モデルディレクトリの作成
RUN mkdir -p /app/models/Stable-diffusion \
    /app/models/VAE \
    /app/models/Lora \
    /app/models/ControlNet \
    /app/outputs \
    /app/extensions \
    /app/logs

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/app

# ポート公開
EXPOSE 7860

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7860 || exit 1

# WebUI起動スクリプト
RUN echo '#!/bin/bash\n\
cd /app\n\
python launch.py --listen --port 7860\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
