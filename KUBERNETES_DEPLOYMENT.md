# Kubernetes Deployment Guide for ManaOS

## 概要

このガイドでは、ManaOSをKubernetesクラスタにデプロイする方法を説明します。HelmチャートとKubernetesマニフェストの両方に対応しています。

## 前提条件

### 必須
- Kubernetes 1.24以上のクラスタ
- kubectl コマンドラインツール
- Helm 3.x（Helmデプロイの場合）
- 十分なリソース（最小: 8 CPU, 16GB RAM）

### 推奨
- LoadBalancerをサポートするクラウドプロバイダー（AWS EKS, GCP GKE, Azure AKS）
- cert-manager（自動SSL証明書管理）
- NGINX Ingress Controller
- Metrics Server（オートスケーリング用）

## クイックスタート

### 方法1: Helmチャートでデプロイ（推奨）

```bash
# リポジトリのクローン
git clone https://github.com/MRL-mana/manaos-integrations.git
cd manaos-integrations

# Helmチャートのインストール
helm install manaos ./helm -n manaos --create-namespace

# デプロイ状態の確認
kubectl get pods -n manaos -w
```

### 方法2: Kubernetesマニフェストでデプロイ

```bash
# Namespaceの作成
kubectl apply -f kubernetes/namespace.yaml

# ConfigMapとSecretsの作成
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Persistent Volumesの作成
kubectl apply -f kubernetes/persistent-volumes.yaml

# サービスのデプロイ
kubectl apply -f kubernetes/unified-api-deployment.yaml
kubectl apply -f kubernetes/mrl-memory-deployment.yaml
kubectl apply -f kubernetes/learning-system-deployment.yaml

# オートスケーリングの設定
kubectl apply -f kubernetes/hpa.yaml

# Ingressの設定
kubectl apply -f kubernetes/ingress.yaml

# デプロイ状態の確認
kubectl get all -n manaos
```

## Helmチャート詳細

### values.yamlのカスタマイズ

```yaml
# helm/values.yaml を編集

# レプリカ数の変更
unifiedApi:
  replicaCount: 5  # デフォルト: 3

# リソース制限の変更
unifiedApi:
  resources:
    limits:
      memory: "4Gi"  # デフォルト: 2Gi
      cpu: "2000m"   # デフォルト: 1000m

# Ingressのホスト名変更
ingress:
  hosts:
    - host: api.yourdomain.com
```

### Helmコマンド

```bash
# カスタムvaluesでインストール
helm install manaos ./helm -n manaos --create-namespace -f custom-values.yaml

# アップグレード
helm upgrade manaos ./helm -n manaos

# ロールバック
helm rollback manaos -n manaos

# アンインストール
helm uninstall manaos -n manaos

# 設定値の確認
helm get values manaos -n manaos

# 履歴の確認
helm history manaos -n manaos
```

## Secretsの設定

### Base64エンコード

```bash
# API Keyをエンコード
echo -n 'your-brave-api-key' | base64

# Secretsファイルに追加
# kubernetes/secrets.yaml
data:
  BRAVE_API_KEY: eW91ci1icmF2ZS1hcGkta2V5
```

### kubectlでSecretsを作成

```bash
kubectl create secret generic manaos-secrets \
  --from-literal=BRAVE_API_KEY=your-brave-api-key \
  --from-literal=CIVITAI_API_KEY=your-civitai-key \
  -n manaos
```

## リソース管理

### リソースクォータの設定

```yaml
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: manaos-quota
  namespace: manaos
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "20"
```

```bash
kubectl apply -f resource-quota.yaml
```

### リミットレンジの設定

```yaml
# limit-range.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: manaos-limits
  namespace: manaos
spec:
  limits:
  - max:
      cpu: "2"
      memory: 4Gi
    min:
      cpu: 100m
      memory: 128Mi
    default:
      cpu: 500m
      memory: 1Gi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```

```bash
kubectl apply -f limit-range.yaml
```

## オートスケーリング

### HPAの設定確認

```bash
# HPAの状態確認
kubectl get hpa -n manaos

# 詳細情報
kubectl describe hpa unified-api-hpa -n manaos

# メトリクスの確認
kubectl top pods -n manaos
kubectl top nodes
```

### カスタムメトリクスでのスケーリング

```yaml
# custom-metrics-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: unified-api-custom-hpa
  namespace: manaos
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: unified-api
  minReplicas: 3
  maxReplicas: 15
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

## ストレージ管理

### 動的プロビジョニング

クラウドプロバイダーのストレージクラスを使用：

```yaml
# AWS EBS
storageClassName: gp3

# GCP Persistent Disk
storageClassName: pd-ssd

# Azure Disk
storageClassName: managed-premium
```

### ボリュームのバックアップ

```bash
# Veleroを使用したバックアップ
velero backup create manaos-backup --include-namespaces manaos

# リストア
velero restore create --from-backup manaos-backup
```

## ネットワーク管理

### Ingressの設定

#### NGINX Ingress Controllerのインストール

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
```

#### cert-managerのインストール（自動SSL）

```bash
# cert-managerのインストール
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Let's Encrypt Issuerの作成
cat <<EOF | kubectl apply -f -
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

### Service Mesh（Istio）

```bash
# Istioのインストール
istioctl install --set profile=demo -y

# ManaOS NamespaceにIstioを有効化
kubectl label namespace manaos istio-injection=enabled

# サービスの再デプロイ
kubectl rollout restart deployment -n manaos
```

## モニタリング

### Prometheusでのメトリクス確認

```bash
# Port-forward
kubectl port-forward -n manaos svc/prometheus 9090:9090

# ブラウザでアクセス
# http://localhost:9090
```

#### 便利なPromQLクエリ

```promql
# CPU使用率（Top 5）
topk(5, rate(container_cpu_usage_seconds_total{namespace="manaos"}[5m]))

# メモリ使用量
sum(container_memory_usage_bytes{namespace="manaos"}) by (pod)

# HTTPリクエストレート
rate(http_requests_total{namespace="manaos"}[5m])

# エラー率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Grafanaダッシュボード

```bash
# Port-forward
kubectl port-forward -n manaos svc/grafana 3000:3000

# ログイン: admin / admin
```

推奨ダッシュボード：
- Kubernetes Cluster Monitoring (ID: 13770)
- Kubernetes / API server (ID: 12006)
- Node Exporter Full (ID: 1860)

## ログ管理

### kubectl logsの活用

```bash
# 特定のPodのログ
kubectl logs -n manaos <pod-name>

# ラベルセレクタでフィルタ
kubectl logs -n manaos -l app=unified-api --tail=100 -f

# 複数コンテナのPod
kubectl logs -n manaos <pod-name> -c <container-name>

# 前回のコンテナログ（クラッシュ時）
kubectl logs -n manaos <pod-name> --previous
```

### ログ集約（ELKスタック）

```bash
# Elasticsearchのインストール
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace

# Kibanaのインストール
helm install kibana elastic/kibana -n logging

# Filebeatのインストール
helm install filebeat elastic/filebeat -n logging
```

## トラブルシューティング

### Podが起動しない

```bash
# Pod状態の確認
kubectl describe pod -n manaos <pod-name>

# イベントの確認
kubectl get events -n manaos --sort-by='.lastTimestamp'

# ログの確認
kubectl logs -n manaos <pod-name>
```

### イメージプル失敗

```bash
# ImagePullSecretsの作成
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry-server> \
  --docker-username=<your-name> \
  --docker-password=<your-password> \
  --docker-email=<your-email> \
  -n manaos

# Deploymentに追加
# spec.template.spec.imagePullSecrets:
# - name: regcred
```

### PersistentVolume問題

```bash
# PVCの状態確認
kubectl get pvc -n manaos

# PVの確認
kubectl get pv

# ストレージクラスの確認
kubectl get storageclass

# 詳細情報
kubectl describe pvc -n manaos <pvc-name>
```

### ネットワーク接続問題

```bash
# Serviceの確認
kubectl get svc -n manaos

# Endpointsの確認
kubectl get endpoints -n manaos

# ネットワークポリシーの確認
kubectl get networkpolicies -n manaos

# デバッグ用Pod起動
kubectl run -it --rm debug --image=curlimages/curl -n manaos -- sh
```

## セキュリティ

### RBAC設定

```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: manaos-sa
  namespace: manaos
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: manaos-role
  namespace: manaos
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: manaos-rolebinding
  namespace: manaos
subjects:
- kind: ServiceAccount
  name: manaos-sa
  namespace: manaos
roleRef:
  kind: Role
  name: manaos-role
  apiGroup: rbac.authorization.k8s.io
```

### Network Policy

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: manaos-network-policy
  namespace: manaos
spec:
  podSelector:
    matchLabels:
      tier: core
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: manaos
    ports:
    - protocol: TCP
      port: 9502
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

### Pod Security Standards

```yaml
# pod-security.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: manaos
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## マルチクラスタデプロイメント

### Kubefedの使用

```bash
# Kubefedのインストール
helm repo add kubefed-charts https://raw.githubusercontent.com/kubernetes-sigs/kubefed/master/charts
helm install kubefed kubefed-charts/kubefed -n kube-federation-system --create-namespace

# クラスタの追加
kubefedctl join cluster1 --cluster-context=cluster1 --host-cluster-context=host
kubefedctl join cluster2 --cluster-context=cluster2 --host-cluster-context=host
```

## コスト最適化

### Nodepoolの活用（GKE例）

```bash
# 通常ワークロード用ノードプール
gcloud container node-pools create standard-pool \
  --cluster=manaos-cluster \
  --machine-type=n1-standard-4 \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10

# GPU対応ノードプール（Video Pipeline用）
gcloud container node-pools create gpu-pool \
  --cluster=manaos-cluster \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --num-nodes=0 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=3
```

### Vertical Pod Autoscaler

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: unified-api-vpa
  namespace: manaos
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: unified-api
  updatePolicy:
    updateMode: "Auto"
```

## CI/CD統合

### GitHub Actionsでのデプロイ

```yaml
# .github/workflows/k8s-deploy.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      
      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig.yaml
          export KUBECONFIG=kubeconfig.yaml
      
      - name: Deploy with Helm
        run: |
          helm upgrade --install manaos ./helm \
            -n manaos \
            --create-namespace \
            --set unifiedApi.image.tag=${{ github.sha }}
```

## まとめ

Kubernetesデプロイにより以下が可能になります：

✅ **高可用性**: 複数レプリカとオートスケーリング  
✅ **スケーラビリティ**: 負荷に応じた自動拡張  
✅ **ポータビリティ**: どのクラウドでも動作  
✅ **監視**: PrometheusとGrafanaによる可視化  
✅ **セキュリティ**: RBAC、NetworkPolicy、Secrets管理  

さらなるサポートが必要な場合は、[TROUBLESHOOTING.md](TROUBLESHOOTING.md)を参照してください。
