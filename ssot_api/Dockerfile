# SSOT API Dockerfile
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
COPY ssot_api.py /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/

# SSOTファイル用ディレクトリ
RUN mkdir -p /app/data

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=ssot_api.py
ENV FLASK_ENV=production

# ポート公開
EXPOSE 5120

# ボリューム（SSOTファイル用）
VOLUME ["/app/data"]

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5120/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "ssot_api.py"]
