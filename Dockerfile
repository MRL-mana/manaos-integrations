FROM python:3.11-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p data logs backups

# 環境変数の設定
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=unified_api_server.py
ENV FLASK_ENV=production
ENV BRAVE_API_KEY=demo_brave_key_12345

# ポートの公開
EXPOSE 5000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)"

# アプリケーションの起動
CMD ["python", "unified_api_server.py"]








