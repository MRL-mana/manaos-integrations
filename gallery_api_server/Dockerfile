# Gallery API Server Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のコピーとインストール
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY gallery_api_server.py /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

# 画像ディレクトリ作成
RUN mkdir -p /app/gallery_images

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=gallery_api_server.py
ENV FLASK_ENV=production
ENV COMFYUI_URL=http://localhost:8188
ENV GALLERY_PORT=5559
ENV GALLERY_IMAGES_DIR=/app/gallery_images

# ポート公開
EXPOSE 5559

# ボリューム（画像保存用）
VOLUME ["/app/gallery_images"]

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5559/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "gallery_api_server.py"]
