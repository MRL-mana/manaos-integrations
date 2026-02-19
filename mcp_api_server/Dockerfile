# MCP API Server Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# MCP APIサーバー向け最小依存をインストール
RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    requests \
    python-dotenv \
    mcp \
    waitress

# アプリケーションコードのコピー
COPY mcp_api_server.py /app/
COPY manaos_unified_mcp_server /app/manaos_unified_mcp_server

# 統合モジュールはボリュームマウントで提供されるため、Dockerfileではコピーしない
# これらのファイルはdocker-compose.ymlでボリュームマウントされます

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=mcp_api_server.py
ENV FLASK_ENV=production
ENV MCP_API_PORT=9502
ENV MCP_API_HOST=0.0.0.0

# ポート公開
EXPOSE 9502

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9502/health || exit 1

# アプリケーション起動
CMD ["python", "-u", "mcp_api_server.py"]
