# ArgoCD GitOps デプロイメントガイド

## 📚 目次

- [ArgoCD GitOpsとは](#argocd-gitopsとは)
- [クイックスタート](#クイックスタート)
- [詳細セットアップ](#詳細セットアップ)
- [運用ガイド](#運用ガイド)
- [トラブルシューティング](#トラブルシューティング)

## 🎯 ArgoCD GitOpsとは

**GitOps**は、Gitリポジトリを「信頼できる唯一の情報源（Single Source of Truth）」として、
インフラストラクチャとアプリケーションの宣言的な管理を行う手法です。

**ArgoCD**は、Kubernetes向けのGitOps継続的デリバリーツールです。

### 主なメリット

✅ **自動デプロイ**: GitコミットでKubernetes環境が自動更新  
✅ **宣言的**: YAML設定でインフラとアプリを管理  
✅ **可視化**: Web UIでリアルタイムにリソース状態を確認  
✅ **ロールバック**: Git履歴から簡単に以前の状態に戻せる  
✅ **監査**: 全変更がGitに記録され、誰が何をしたか追跡可能  

## 🚀 クイックスタート

### 前提条件

- Kubernetesクラスタ（1.24+）
- kubectl CLI
- Helm 3.x
- GitHub/GitLabアカウント

### 1. ArgoCDインストール

```bash
# ArgoCDネームスペース作成
kubectl create namespace argocd

# ArgoCD本体インストール
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# インストール確認
kubectl get pods -n argocd
```

### 2. ArgoCD CLIインストール

```bash
# Windows (Scoop)
scoop install argocd

# macOS (Homebrew)
brew install argocd

# Linux
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
```

### 3. ArgoCD UIアクセス

```bash
# ポートフォワード
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 初期パスワード取得
argocd admin initial-password -n argocd

# ブラウザで開く
# https://localhost:8080
# Username: admin
# Password: <上記で取得したパスワード>
```

### 4. ManaOSアプリケーションデプロイ

```bash
# ArgoCD CLIログイン
argocd login localhost:8080 --insecure

# パスワード変更（推奨）
argocd account update-password

# ManaOSアプリケーション作成
kubectl apply -f kubernetes/argocd/application.yaml

# デプロイ状況確認
argocd app get manaos

# 同期（自動同期が無効の場合）
argocd app sync manaos
```

## 📋 詳細セットアップ

### GitHubリポジトリ連携

#### 1. GitHubリポジトリの設定

```bash
# SSHキー生成（まだの場合）
ssh-keygen -t ed25519 -C "argocd@manaos.io" -f ~/.ssh/argocd_ed25519

# 公開鍵をGitHubに登録
cat ~/.ssh/argocd_ed25519.pub
# GitHub → Settings → Deploy keys → Add deploy key
```

#### 2. ArgoCDにリポジトリを登録

```bash
# SSH経由
argocd repo add git@github.com:MRL-mana/manaos-integrations.git \
  --ssh-private-key-path ~/.ssh/argocd_ed25519

# HTTPS経由（Personal Access Token使用）
argocd repo add https://github.com/MRL-mana/manaos-integrations.git \
  --username <your-username> \
  --password <your-token>

# リポジトリ確認
argocd repo list
```

### Webhooksの設定

GitHubへのプッシュで自動的にArgoCDが同期するように設定します。

#### 1. Webhook Secretの作成

```bash
# ランダムなシークレット生成
WEBHOOK_SECRET=$(openssl rand -hex 32)

# ArgoCDに設定
kubectl -n argocd patch secret argocd-secret \
  -p "{\"stringData\": {\"webhook.github.secret\": \"$WEBHOOK_SECRET\"}}"
```

#### 2. GitHubにWebhookを設定

1. GitHubリポジトリ → Settings → Webhooks → Add webhook
2. 設定値:
   - **Payload URL**: `https://argocd.yourdomain.com/api/webhook`
   - **Content type**: `application/json`
   - **Secret**: 上記で生成した`WEBHOOK_SECRET`
   - **Events**: "Just the push event"

### SSL/TLS設定（Let's Encrypt）

```bash
# cert-managerインストール（まだの場合）
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer作成
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

# ArgoCD Ingress作成
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server-ingress
  namespace: argocd
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  rules:
  - host: argocd.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              name: https
  tls:
  - hosts:
    - argocd.yourdomain.com
    secretName: argocd-server-tls
EOF
```

### RBAC設定

```bash
# カスタム設定をargoCDに適用
kubectl apply -f kubernetes/argocd/argocd-install.yaml
```

`argocd-rbac-cm` ConfigMapで以下のロールを定義:

- **admin**: 全権限
- **developer**: アプリケーションの作成・同期・更新
- **readonly**: 読み取り専用

## 🔧 運用ガイド

### アプリケーション管理

#### デプロイ状態の確認

```bash
# アプリケーション一覧
argocd app list

# 詳細情報
argocd app get manaos

# リソース状態
argocd app resources manaos

# ログ確認
argocd app logs manaos
```

#### 手動同期

```bash
# 完全同期
argocd app sync manaos

# 特定リソースのみ同期
argocd app sync manaos --resource Deployment:manaos:unified-api

# Prune（不要なリソース削除）を含む同期
argocd app sync manaos --prune
```

#### ロールバック

```bash
# 履歴確認
argocd app history manaos

# 特定リビジョンにロールバック
argocd app rollback manaos <revision-id>

# 1つ前のリビジョンに戻す
argocd app rollback manaos
```

### トラブルシューティング

#### アプリケーションがOutOfSyncの場合

```bash
# 差分確認
argocd app diff manaos

# 強制同期（ヘルスチェック無視）
argocd app sync manaos --force

# リソースの削除と再作成
argocd app sync manaos --replace
```

#### SyncがFailedの場合

```bash
# エラー詳細確認
argocd app get manaos

# ログ確認
kubectl logs -n argocd deployment/argocd-application-controller

# リソースの状態確認
kubectl get all -n manaos
```

#### リポジトリ接続エラー

```bash
# リポジトリ接続テスト
argocd repo get https://github.com/MRL-mana/manaos-integrations.git

# 認証情報の更新
argocd repo add https://github.com/MRL-mana/manaos-integrations.git \
  --username <new-username> \
  --password <new-token> \
  --upsert
```

### モニタリングと通知

#### Prometheus統合

```bash
# ArgoCDメトリクスを確認
kubectl port-forward -n argocd svc/argocd-metrics 8082:8082

# ブラウザで開く
# http://localhost:8082/metrics
```

#### Slack通知設定

```bash
# Slack Tokenを設定
kubectl -n argocd patch secret argocd-notifications-secret \
  -p "{\"stringData\": {\"slack-token\": \"xoxb-your-token\"}}"

# 通知設定を適用
kubectl apply -f kubernetes/argocd/argocd-install.yaml

# 通知テスト
argocd app actions run manaos notify
```

### マルチクラスタ管理

```bash
# クラスタ追加
argocd cluster add <context-name>

# クラスタ一覧
argocd cluster list

# 特定クラスタへのデプロイ
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: manaos-staging
  namespace: argocd
spec:
  destination:
    server: https://staging-cluster-url
    namespace: manaos
  # ... その他の設定
EOF
```

## 🎨 GitOpsワークフロー例

### 本番環境への段階的デプロイ

```
開発 → ステージング → 本番
 ↓         ↓          ↓
develop  staging    main
branch   branch    branch
```

#### 1. 開発環境（自動デプロイ）

```yaml
# application-dev.yaml
spec:
  source:
    targetRevision: develop
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

#### 2. ステージング環境（自動デプロイ + 承認）

```yaml
# application-staging.yaml
spec:
  source:
    targetRevision: staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # 自己修復は無効
```

#### 3. 本番環境（手動デプロイ）

```yaml
# application-prod.yaml
spec:
  source:
    targetRevision: main
  syncPolicy:
    # automated を設定しない = 手動のみ
    syncOptions:
      - CreateNamespace=true
```

### カナリアデプロイメント

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: unified-api-rollout
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10      # 10%のトラフィック
      - pause: {duration: 5m}
      - setWeight: 30      # 30%のトラフィック
      - pause: {duration: 10m}
      - setWeight: 50      # 50%のトラフィック
      - pause: {duration: 10m}
      - setWeight: 100     # 全トラフィック
```

## 📊 ベストプラクティス

### 1. ディレクトリ構造

```
manaos-integrations/
├── helm/                    # Helm Chart（テンプレート）
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── kubernetes/
│   ├── base/               # 共通設定
│   ├── overlays/
│   │   ├── development/    # 開発環境固有設定
│   │   ├── staging/        # ステージング環境固有設定
│   │   └── production/     # 本番環境固有設定
│   └── argocd/
│       ├── application-dev.yaml
│       ├── application-staging.yaml
│       └── application-prod.yaml
```

### 2. Secrets管理

**重要**: 機密情報をGitにコミットしない！

#### Sealed Secrets使用

```bash
# Sealed Secrets Controllerインストール
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# kubeseal CLIインストール
brew install kubeseal

# Secretを暗号化
kubectl create secret generic manaos-secrets \
  --from-literal=api-key=your-secret \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# 暗号化されたSecretをコミット
git add sealed-secret.yaml
git commit -m "Add sealed secrets"
```

### 3. アプリケーション設定の分離

```yaml
# values-dev.yaml (開発環境)
unifiedApi:
  replicaCount: 1
  resources:
    limits:
      memory: 512Mi

# values-prod.yaml (本番環境)
unifiedApi:
  replicaCount: 5
  resources:
    limits:
      memory: 2Gi
```

### 4. ヘルスチェックのカスタマイズ

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas  # HPA管理のため無視
```

## 🆘 FAQ

### Q: ArgoCDとHelm、どちらを使うべき？

**A**: 両方を組み合わせて使うのがベストプラクティスです：
- **Helm**: テンプレートとパッケージ管理
- **ArgoCD**: GitOpsによる継続的デリバリー

### Q: 自動同期は有効にすべき？

**A**: 環境によって使い分け：
- **開発環境**: 有効（即座に反映）
- **本番環境**: 無効（手動承認で安全性確保）

### Q: ApplicationとApplicationSetの違いは？

**A**:
- **Application**: 単一のアプリケーションを管理
- **ApplicationSet**: 複数のApplicationを一括管理（マルチクラスタなど）

## 🔗 関連リンク

- [ArgoCD公式ドキュメント](https://argo-cd.readthedocs.io/)
- [GitOpsとは](https://www.gitops.tech/)
- [Kubernetes Deployment Guide](KUBERNETES_DEPLOYMENT.md)
- [Complete Deployment Guide](COMPLETE_DEPLOYMENT_GUIDE.md)

---

Happy GitOps! 🚀
