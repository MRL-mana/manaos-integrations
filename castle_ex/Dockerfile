# Castle Ex 学習パイプライン コンテナ
# ビルド: docker build -f castle_ex/Dockerfile -t castle_ex .  (プロジェクトルートで)
# GPU: デフォルト (pytorch イメージ)
# CPU: docker build -f castle_ex/Dockerfile --build-arg BASE=python:3.11-slim -t castle_ex .
ARG BASE=pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
FROM ${BASE}

WORKDIR /app

# CPU ベース (python:slim) の場合は PyTorch をインストール。GPU ベースなら already satisfied
RUN pip install --no-cache-dir torch

# 依存関係
RUN pip install --no-cache-dir \
    transformers>=4.36.0 \
    datasets>=2.16.0 \
    accelerate \
    peft \
    bitsandbytes

# Castle Ex モジュール（ビルドコンテキスト=プロジェクトルート）
COPY castle_ex /app/castle_ex

ENV PYTHONPATH=/app
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
ENV TQDM_DISABLE=1

# 実行例: docker run -v $(pwd)/data:/app/data -v $(pwd)/output:/app/output castle_ex \
#   python castle_ex/train_castle_ex_full.py --base-model ... --train-data ...
CMD ["python", "-u", "castle_ex/train_castle_ex_full.py", "--help"]
