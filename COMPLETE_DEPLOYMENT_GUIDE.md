# ManaOS 完全デプロイメントガイド

## 🎯 デプロイメント全体像

ManaOSは3つのデプロイメント環境に対応しています：

1. **ローカル開発** - Python直接実行
2. **Docker環境** - コンテナ化されたサービス
3. **Kubernetes/クラウド** - スケーラブルな本番環境

## 📊 デプロイメント比較表

| 特徴 | ローカル | Docker | Kubernetes |
|------|---------|--------|------------|
| **セットアップ時間** | 5分 | 15分 | 30分+ |
| **スケーラビリティ** | ❌ | ⚠️ 制限あり | ✅ 自動 |
| **リソース効率** | 低 | 中 | 高 |
| **運用の複雑さ** | 低 | 中 | 高 |
| **コスト** | 無料 | 無料 | 従量課金 |
| **適用シーン** | 開発・テスト | 単一サーバー | クラウド本番 |
| **モニタリング** | 基本 | Prometheus/Grafana | 統合 |
| **CI/CD統合** | 手動 | 半自動 | 完全自動 |

## 🚀 クイックスタートガイド

### シナリオ1: 個人開発者

```bash
# 1. リポジトリクローン
git clone https://github.com/MRL-mana/manaos-integrations.git
cd manaos-integrations

# 2. 依存関係インストール
pip install -r requirements-core.txt

# 3. サービス起動
python unified_api_server.py

# 完了！ http://localhost:9502 でアクセス
```

**推奨**: VSCode Tasks を使用（`Ctrl+Shift+P` → "Run Task" → "ManaOS: すべてのサービスを起動"）

### シナリオ2: チーム開発（Docker）

```bash
# 1. リポジトリクローン
git clone https://github.com/MRL-mana/manaos-integrations.git
cd manaos_integrations

# 2. 環境変数設定
cp .env.template .env
# .envを編集してAPI Keyを設定

# 3. Docker環境セットアップ
.\setup_docker_environment.ps1 -StartServices

# 4. モニタリングダッシュボードにアクセス
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### シナリオ3: 本番環境（Kubernetes/AWS EKS）

```bash
# 1. EKSクラスタ作成
eksctl create cluster \
  --name manaos-prod \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed

# 2. kubectlコンテキスト設定
aws eks update-kubeconfig --name manaos-prod --region us-west-2

# 3. NGINX Ingress Controller インストール
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/aws/deploy.yaml

# 4. cert-manager インストール（SSL自動化）
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# 5. ManaOS デプロイ
cd manaos_integrations
.\deploy_to_kubernetes.ps1 -Method helm -WaitForReady

# 6. External IPを取得
kubectl get svc unified-api -n manaos -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## 📋 詳細デプロイメント手順

### 1. ローカル開発環境

#### Windowsセットアップ

```powershell
# Python 3.10以上インストール
winget install Python.Python.3.10

# 依存関係インストール
cd manaos_integrations
pip install -r requirements-core.txt

# VSCode Tasks設定（推奨）
# .vscode/tasks.json は既に設定済み

# サービス起動
Ctrl+Shift+P → "Run Task" → "ManaOS: すべてのサービスを起動"
```

#### Linuxセットアップ

```bash
# Python 3.10以上インストール
sudo apt update
sudo apt install python3.10 python3-pip

# 依存関係インストール
cd manaos_integrations
pip3 install -r requirements-core.txt

# サービス起動
python3 unified_api_server.py
python3 -m mrl_memory_integration
python3 -m learning_system_api
python3 -m llm_routing_mcp_server
```

### 2. Docker環境

#### 初期セットアップ

```powershell
# Docker Desktop インストール（まだの場合）
winget install Docker.DockerDesktop

# セットアップスクリプト実行
.\setup_docker_environment.ps1

# または手動セットアップ
docker-compose build
docker-compose up -d
```

#### サービス管理

```powershell
# 全サービス起動
docker-compose up -d

# 特定サービスのみ起動
docker-compose up -d unified-api mrl-memory

# ログ確認
docker-compose logs -f unified-api

# サービス再起動
docker-compose restart

# リソース使用状況
docker stats

# クリーンアップ
docker-compose down -v
```

#### バックアップと復元

```powershell
# バックアップ作成
.\backup_docker.ps1

# バックアップから復元
.\restore_docker_backup.ps1 -BackupFile ".\backups\docker\manaos-backup-20260215-120000.zip"
```

### 3. Kubernetes環境

#### クラウドプロバイダー別セットアップ

##### AWS EKS

```bash
# eksctl インストール
brew install eksctl  # macOS
# または Windows: choco install eksctl

# クラスタ作成
eksctl create cluster -f kubernetes/eks-cluster.yaml

# kubectl設定
aws eks update-kubeconfig --name manaos-prod --region us-west-2

# デプロイ
.\deploy_to_kubernetes.ps1 -Method helm
```

##### Google GKE

```bash
# gcloud CLI インストール
gcloud components install kubectl

# クラスタ作成
gcloud container clusters create manaos-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10

# kubectl設定
gcloud container clusters get-credentials manaos-prod --zone us-central1-a

# デプロイ
helm install manaos ./helm -n manaos --create-namespace
```

##### Azure AKS

```bash
# Azure CLI インストール
az aks install-cli

# クラスタ作成
az aks create \
  --resource-group manaos-rg \
  --name manaos-prod \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10 \
  --generate-ssh-keys

# kubectl設定
az aks get-credentials --resource-group manaos-rg --name manaos-prod

# デプロイ
helm install manaos ./helm -n manaos --create-namespace
```

## 🔧 CI/CD パイプライン設定

### GitHub Actions

```bash
# 1. シークレット設定
# GitHub Repository → Settings → Secrets and variables → Actions

必要なシークレット:
- DOCKER_HUB_USERNAME
- DOCKER_HUB_TOKEN
- KUBECONFIG_STAGING
- KUBECONFIG_PRODUCTION
- SLACK_WEBHOOK_URL
```

### GitLab CI/CD

```yaml
# .gitlab-ci.yml を作成
include:
  - template: Auto-DevOps.gitlab-ci.yml

variables:
  DOCKER_DRIVER: overlay2
  KUBERNETES_VERSION: 1.28.0
```

## 📊 モニタリング設定

### Grafanaダッシュボードインポート

```bash
# 1. Grafanaにアクセス
http://localhost:3000  # Docker
# または kubectl port-forward -n manaos svc/grafana 3000:3000

# 2. ログイン（admin/admin）

# 3. ダッシュボードインポート
# Configuration → Data Sources → Add Prometheus
# URL: http://prometheus:9090

# 4. カスタムダッシュボードインポート
# Dashboards → Import → Upload JSON file
# monitoring/grafana/dashboards/manaos-services-dashboard.json を選択
```

### アラート設定

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: manaos-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        annotations:
          summary: "Pod is crash looping"
```

## 🧪 テスト実行

### ユニットテスト

```bash
# 全テスト実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=. --cov-report=html
```

### 統合テスト

```bash
# Docker環境で統合テスト
docker-compose up -d
pytest tests/integration/ -v
```

### 負荷テスト

```bash
# 基準負荷テスト
python load_test.py --service unified-api --test burst

# 持続負荷テスト
python load_test.py --service all --test sustained

# スパイクテスト
python load_test.py --service all --test spike
```

### パフォーマンステスト

```bash
# ベンチマーク実行
python benchmark_performance.py

# レポート確認
# benchmark_report_YYYYMMDD_HHMMSS.json
```

## 🔐 セキュリティ設定

### Secrets管理

```bash
# Kubernetes Secrets作成
kubectl create secret generic manaos-secrets \
  --from-literal=BRAVE_API_KEY=your-key \
  --from-literal=CIVITAI_API_KEY=your-key \
  -n manaos

# Docker環境
# .env ファイルに設定
BRAVE_API_KEY=your-key
CIVITAI_API_KEY=your-key
```

### SSL証明書（Let's Encrypt）

```bash
# cert-manager ClusterIssuer作成
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## 📈 スケーリング戦略

### 水平スケーリング（HPA）

```bash
# CPU使用率ベース
kubectl autoscale deployment unified-api \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  -n manaos

# カスタムメトリクスベース
kubectl apply -f kubernetes/hpa.yaml
```

### 垂直スケーリング（VPA）

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: unified-api-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: unified-api
  updatePolicy:
    updateMode: "Auto"
```

## 🆘 トラブルシューティング

### よくある問題

1. **Podが起動しない**
   ```bash
   kubectl describe pod <pod-name> -n manaos
   kubectl logs <pod-name> -n manaos
   ```

2. **イメージプルエラー**
   ```bash
   kubectl create secret docker-registry regcred \
     --docker-server=<registry> \
     --docker-username=<username> \
     --docker-password=<password> \
     -n manaos
   ```

3. **サービスにアクセスできない**
   ```bash
   kubectl get svc -n manaos
   kubectl port-forward -n manaos svc/unified-api 9502:9502
   ```

詳細は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

## 📚 関連ドキュメント

- [Docker Deployment Guide](DOCKER_DEPLOYMENT.md)
- [Kubernetes Deployment Guide](KUBERNETES_DEPLOYMENT.md)
- [Distributed Deployment Guide](DISTRIBUTED_DEPLOYMENT.md)
- [Environment Variables Guide](ENVIRONMENT_VARIABLES.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

## 🎉 次のステップ

デプロイメントが完了したら：

1. ✅ [モニタリングダッシュボード](http://localhost:3000) を設定
2. ✅ [負荷テスト](#負荷テスト) を実行してパフォーマンスを確認
3. ✅ [アラート設定](#アラート設定) で障害通知を有効化
4. ✅ [バックアップ](#バックアップと復元) スケジュールを設定
5. ✅ [CI/CD](#cicd-パイプライン設定) パイプラインを構築

Happy Deploying! 🚀
