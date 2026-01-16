# Web Voice Interface Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のコピーとインストール
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY web_voice_interface.py /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=web_voice_interface.py
ENV FLASK_ENV=production
ENV PORT=5115

# ポート公開
EXPOSE 5115

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5115/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "web_voice_interface.py"]
