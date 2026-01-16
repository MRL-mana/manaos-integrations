# Service Monitor Dockerfile
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
COPY service_monitor.py /app/
COPY service_monitor_config.json /app/
COPY manaos_logger.py /app/

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=service_monitor.py
ENV FLASK_ENV=production

# ポート公開
EXPOSE 5111

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5111/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "service_monitor.py"]
