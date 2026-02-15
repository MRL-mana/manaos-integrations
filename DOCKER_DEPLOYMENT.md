# Docker Deployment Guide for ManaOS

## 概要

このガイドでは、ManaOSサービスをDockerコンテナとして実行する方法を説明します。

## 前提条件

- Docker Desktop for Windows (最新版)
- Docker Compose v2.x以上
- 最低8GBのRAM
- 最低20GBの空きディスク容量

## クイックスタート

### 1. 環境変数ファイルの作成

```powershell
# .envファイルを作成
Copy-Item .env.template .env

# エディタで編集
notepad .env
```

必要なAPI Keyを設定してください：
- `BRAVE_API_KEY`（Brave Search用）
- `CIVITAI_API_KEY`（CivitAI画像検索用）
- `GRAFANA_PASSWORD`（Grafanaダッシュボード用）

### 2. すべてのサービスを起動

```powershell
# すべてのサービスを起動
docker-compose up -d

# ログを確認
docker-compose logs -f
```

### 3. サービスの確認

各サービスが正常に起動しているか確認：

```powershell
# ヘルスチェック
docker-compose ps

# 個別のサービスログ
docker-compose logs unified-api
docker-compose logs mrl-memory
docker-compose logs learning-system
```

### 4. アクセス確認

| サービス | URL | 説明 |
|---------|-----|------|
| Unified API | http://localhost:9502 | メインAPI |
| MRL Memory | http://localhost:9507 | メモリ管理 |
| Learning System | http://localhost:9508 | 学習システム |
| LLM Routing | http://localhost:9509 | LLMルーティング |
| Gallery API | http://localhost:5559 | 画像ギャラリー |
| Video Pipeline | http://localhost:9511 | 動画パイプライン |
| Prometheus | http://localhost:9090 | メトリクス収集 |
| Grafana | http://localhost:3000 | ダッシュボード |
| cAdvisor | http://localhost:8080 | コンテナメトリクス |

## サービス管理コマンド

### すべてのサービス

```powershell
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# ログ確認（リアルタイム）
docker-compose logs -f

# ログ確認（特定サービス）
docker-compose logs -f unified-api

# サービス状態確認
docker-compose ps

# リソース使用状況
docker stats
```

### 個別サービス

```powershell
# 特定サービスのみ起動
docker-compose up -d unified-api mrl-memory

# 特定サービスの再起動
docker-compose restart learning-system

# 特定サービスの停止
docker-compose stop gallery-api

# 特定サービスのログ確認
docker-compose logs -f llm-routing --tail 100
```

### イメージ管理

```powershell
# イメージの再ビルド
docker-compose build

# 特定サービスの再ビルド
docker-compose build unified-api

# キャッシュなしでビルド
docker-compose build --no-cache

# イメージの削除
docker-compose down --rmi all
```

### データボリューム管理

```powershell
# ボリュームの確認
docker volume ls

# ボリュームの詳細
docker volume inspect manaos_integrations_prometheus-data

# すべて削除（データも含む）⚠️
docker-compose down -v
```

## モニタリング

### Prometheusでメトリクス確認

1. http://localhost:9090 にアクセス
2. Graphタブで以下のクエリを試す：

```promql
# CPU使用率
rate(container_cpu_usage_seconds_total[5m])

# メモリ使用量
container_memory_usage_bytes

# ネットワークトラフィック
rate(container_network_receive_bytes_total[5m])

# サービスアップタイム
up{job="unified-api"}
```

### Grafanaでダッシュボード作成

1. http://localhost:3000 にアクセス
2. ユーザー名: `admin`、パスワード: `.env`で設定した値
3. Configuration → Data Sources → Add data source → Prometheus
4. URL: `http://prometheus:9090`
5. Save & Test

#### おすすめダッシュボード

- **Docker Container & Host Metrics** (ID: 893)
- **Docker Dashboard** (ID: 179)
- **cAdvisor exporter** (ID: 14282)

インポート手順：
1. Dashboards → Import
2. Dashboard IDを入力
3. Load → Prometheusを選択 → Import

### cAdvisorでコンテナ詳細確認

1. http://localhost:8080 にアクセス
2. 各コンテナのCPU/メモリ/ネットワーク使用状況を確認

## トラブルシューティング

### サービスが起動しない

```powershell
# ログで原因を確認
docker-compose logs unified-api

# コンテナの詳細情報
docker inspect manaos-unified-api

# エラーメッセージの検索
docker-compose logs | Select-String -Pattern 'ERROR'
```

### ポート競合エラー

```powershell
# ポート使用状況を確認
netstat -ano | findstr :9502

# プロセスを終了
Stop-Process -Id <PID> -Force

# または別のポートを使用（.envで変更）
UNIFIED_API_PORT=9503
```

### イメージビルドエラー

```powershell
# Dockerfileの構文チェック
docker build --no-cache -f Dockerfile .

# 依存関係の問題
docker-compose build --pull
```

### メモリ不足

```powershell
# メモリ使用量確認
docker stats --no-stream

# 使用していないイメージ/コンテナ/ボリュームを削除
docker system prune -a

# Dockerのメモリ制限を増やす（Docker Desktop設定）
# Settings → Resources → Memory → 16GB以上推奨
```

### ネットワークエラー

```powershell
# ネットワーク確認
docker network ls
docker network inspect manaos_integrations_manaos-network

# ネットワーク再作成
docker-compose down
docker network prune
docker-compose up -d
```

## パフォーマンス最適化

### ワーカープロセス数の調整

`.env`ファイルで設定：
```env
WORKER_PROCESSES=8  # CPUコア数に応じて調整
```

### メモリキャッシュの最適化

```env
MEMORY_CACHE_MAX_SIZE=5000  # より大きなキャッシュ
MEMORY_CACHE_TTL=7200        # 2時間
```

### ログローテーション

```powershell
# Dockerのログサイズ制限
# docker-compose.ymlに追加
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## バックアップとリストア

### データのバックアップ

```powershell
# ボリュームのバックアップ
docker run --rm -v manaos_integrations_prometheus-data:/data -v ${PWD}/backups:/backup alpine tar czf /backup/prometheus-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').tar.gz -C /data .

# コンテナ内のデータディレクトリをバックアップ
docker cp manaos-unified-api:/app/data ./backups/unified-api-data-$(Get-Date -Format 'yyyyMMdd-HHmmss')
```

### データのリストア

```powershell
# ボリュームのリストア
docker run --rm -v manaos_integrations_prometheus-data:/data -v ${PWD}/backups:/backup alpine sh -c "cd /data && tar xzf /backup/prometheus-backup-20260214-123456.tar.gz"

# コンテナへデータをコピー
docker cp ./backups/unified-api-data-20260214-123456 manaos-unified-api:/app/data
```

## セキュリティ設定

### APIキーの管理

環境変数ではなくDocker Secretsを使用：

```yaml
# docker-compose.ymlに追加
secrets:
  brave_api_key:
    file: ./secrets/brave_api_key.txt
  civitai_api_key:
    file: ./secrets/civitai_api_key.txt

services:
  unified-api:
    secrets:
      - brave_api_key
      - civitai_api_key
```

### ネットワーク分離

```yaml
# docker-compose.ymlで内部ネットワークを作成
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 外部接続不可
```

### 脆弱性スキャン

```powershell
# Trivyでイメージをスキャン
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image manaos_integrations-unified-api
```

## CI/CD統合

### GitHub Actionsでのビルド

```yaml
# .github/workflows/docker-build.yml
name: Docker Build and Push

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./manaos_integrations
          push: true
          tags: username/manaos-unified-api:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## マルチステージビルド最適化

より小さなイメージを作成：

```dockerfile
# Dockerfile（最適化版）
# ビルドステージ
FROM python:3.10-slim as builder
WORKDIR /app
COPY requirements-core.txt .
RUN pip install --user --no-cache-dir -r requirements-core.txt

# 実行ステージ
FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "unified_api_server.py"]
```

## 高可用性構成

### Docker Swarmでのデプロイ

```powershell
# Swarmモードを初期化
docker swarm init

# スタックをデプロイ
docker stack deploy -c docker-compose.yml manaos

# サービス確認
docker service ls
docker service logs manaos_unified-api
```

### レプリカとロードバランシング

```yaml
# docker-compose.ymlに追加
services:
  unified-api:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## まとめ

Docker環境では以下の利点があります：

✅ **一貫性**: どの環境でも同じように動作
✅ **分離**: サービス間の依存関係が明確
✅ **スケーラビリティ**: 簡単にレプリカを増やせる
✅ **モニタリング**: PrometheusとGrafanaで可視化
✅ **ポータビリティ**: クラウドやオンプレどちらでも動作

さらなるサポートが必要な場合は、[TROUBLESHOOTING.md](TROUBLESHOOTING.md)を参照してください。
