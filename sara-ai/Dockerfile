# Sara-AI-Platform Dockerfile
# ローカルLLMプラットフォームコンテナ

FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Sara-AI-Platformをクローン（存在する場合）
# 注意: 実際のリポジトリパスに合わせて調整が必要
RUN git clone https://github.com/your-repo/Sara-AI-Platform.git /app || \
    echo "リポジトリが見つかりません。手動で配置してください。"

# 依存関係のインストール
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir fastapi uvicorn requests

# ディレクトリの作成
RUN mkdir -p /app/data /app/models /app/logs

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/app
ENV PORT=8000

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# アプリケーション起動（実際の起動スクリプトに合わせて調整）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
