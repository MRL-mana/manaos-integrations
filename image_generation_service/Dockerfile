# Image Generation Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 依存関係
COPY image_generation_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY image_generation_service/ /app/image_generation_service/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

# 共有モジュール (RL, revenue)
COPY rl_anything/ /app/rl_anything/
COPY revenue_api_server.py /app/

# データディレクトリ
RUN mkdir -p /app/data /app/logs

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV COMFYUI_URL=http://host.docker.internal:8188
ENV UNIFIED_API_URL=http://host.docker.internal:9502
ENV IMAGE_SERVICE_PORT=5560

# ポート公開
EXPOSE 5560

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5560/health || exit 1

# アプリケーション起動
CMD ["uvicorn", "image_generation_service.router:router_app", "--host", "0.0.0.0", "--port", "5560", "--workers", "1"]
