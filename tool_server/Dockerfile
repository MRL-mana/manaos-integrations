FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のコピーとインストール
COPY tool_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY tool_server/main.py /app/main.py

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV TOOL_SERVER_PORT=9503

# ポート公開
EXPOSE 9503

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9503/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "main.py"]
