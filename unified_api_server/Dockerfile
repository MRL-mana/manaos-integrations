# Unified API Server Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係（docker CLIを含む）
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Docker CLIをインストール（レミ先輩仕様：確実に動くように）
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# 依存関係のコピーとインストール
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY unified_api_server.py /app/
COPY unified_api /app/unified_api
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

# 統合モジュール（オプション、存在する場合のみ）
# これらのファイルはビルドコンテキストに存在する場合のみコピーされます
# 存在しない場合はエラーを無視します

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=unified_api_server.py
ENV FLASK_ENV=production

# ポート公開
EXPOSE 9502

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9502/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "unified_api_server.py"]
