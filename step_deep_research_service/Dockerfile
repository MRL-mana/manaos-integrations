# Step Deep Research Service Dockerfile
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
COPY step_deep_research_service.py /app/
COPY step_deep_research/ /app/step_deep_research/
COPY step_deep_research_config.json /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=step_deep_research_service.py
ENV FLASK_ENV=production

# ポート公開
EXPOSE 5121

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5121/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "step_deep_research_service.py"]
