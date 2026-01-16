# RunPod MCP Server Dockerfile
# 軽量なMCPサーバー専用コンテナ

FROM python:3.11-slim

WORKDIR /app

# システム依存関係（最小限）
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# MCPサーバー専用の依存関係
# 注意: RunPod APIは外部サービスなので、重いライブラリは不要
COPY mcp/requirements-mcp-runpod.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# MCPサーバーコード
COPY mcp/runpod_mcp_server.py /app/
COPY services/ /app/services/

# 設定ファイル（Vault）をマウント用ディレクトリ作成
RUN mkdir -p /app/.mana_vault

# ログディレクトリ
RUN mkdir -p /app/logs

# 環境変数
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV BRAVE_API_KEY=demo_brave_key_12345

# ヘルスチェック用（MCPサーバーはstdioなので直接チェック不可）
# 代わりにプロセス確認
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; data=open('/proc/1/cmdline','rb').read().decode(errors='ignore'); sys.exit(0 if 'runpod_mcp_server.py' in data else 1)"

# MCPサーバー起動（stdio経由）
CMD ["python", "-u", "runpod_mcp_server.py"]

