# エンタープライズセキュリティ＆オブザーバビリティガイド

本ガイドは、ManaOS マイクロサービスプラットフォームの本番環境展開における、セキュリティ強化、バックアップ・災害対策、オブザーバビリティの総合的な実装方法を説明します。

---

## 📋 目次

1. [セキュリティ強化](#セキュリティ強化)
   - Pod Security Standards
   - Network Policies
   - RBAC & ServiceAccounts
   - セキュリティスキャン自動化
2. [バックアップ・災害対策](#バックアップ災害対策)
   - Velero バックアップ設定
   - 災害復旧手順
3. [オブザーバビリティ](#オブザーバビリティ)
   - Jaeger 分散トレーシング
   - Loki ログ集約
4. [クイックスタート](#クイックスタート)
5. [運用ベストプラクティス](#運用ベストプラクティス)

---

## セキュリティ強化

### 1. Pod Security Standards

Kubernetes 1.25+ の Pod Security Admission を使用し、3段階のセキュリティレベルを設定します。

#### 適用方法

```bash
# Pod Security Standards の適用
kubectl apply -f kubernetes/security/pod-security-standards.yaml
```

#### セキュリティプロファイル

| **Namespace** | **Profile** | **説明** |
|---------------|------------|---------|
| `manaos-production` | **Restricted** | 最も厳格な制約。本番環境で使用 |
| `manaos-staging` | **Restricted** | ステージング環境も本番同等 |
| `manaos-development` | **Baseline** | 開発の柔軟性を確保 |
| `monitoring` | **Baseline** | 監視ツールは一部権限が必要 |

#### Restricted プロファイルの要件

- ✅ 非rootユーザーとして実行 (`runAsNonRoot: true`)
- ✅ 全ケイパビリティをドロップ (`capabilities.drop: [ALL]`)
- ✅ 特権昇格の禁止 (`allowPrivilegeEscalation: false`)
- ✅ 読み取り専用ルートファイルシステム (`readOnlyRootFilesystem: true`)
- ✅ Seccomp プロファイルの適用 (`seccompProfile.type: RuntimeDefault`)
- ✅ リソース制限の設定 (requests & limits)

#### セキュリティ準拠 Pod の例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
  namespace: manaos-production
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    fsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: manaos/app:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

---

### 2. Network Policies（ゼロトラストネットワーク）

マイクロサービス間の通信をマイクロセグメンテーションで制御します。

#### 適用方法

```bash
# Network Policies の適用
kubectl apply -f kubernetes/security/network-policies.yaml
```

#### ゼロトラスト原則

1. **デフォルト拒否**: すべての Ingress/Egress トラフィックを拒否
2. **明示的許可**: 必要な通信のみ許可
3. **最小権限**: サービスごとに必要な通信だけ設定

#### Network Policy の例

```yaml
# デフォルト拒否（基盤）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: manaos-production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
# DNS 解決の許可（必須）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: manaos-production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

#### サービス間通信マトリックス

| **From** | **To** | **Port** | **Protocol** |
|----------|--------|----------|-------------|
| Unified API | MRL Memory | 8001 | TCP |
| Unified API | Learning System | 8002 | TCP |
| Unified API | LLM Routing | 8003 | TCP |
| MRL Memory | Redis | 6379 | TCP |
| MRL Memory | PostgreSQL | 5432 | TCP |
| LLM Routing | External APIs | 443 | TCP (HTTPS) |
| Prometheus | All Services | 8001-9510 | TCP |

#### テスト方法

```bash
# テスト用 Pod を起動
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: netpol-test
  namespace: manaos-production
spec:
  containers:
  - name: netshoot
    image: nicolaka/netshoot:latest
    command: ["sleep", "3600"]
EOF

# Pod 内から接続テスト
kubectl exec -n manaos-production netpol-test -- curl -I http://unified-api:9510/health
kubectl exec -n manaos-production netpol-test -- curl -I http://mrl-memory:8001/health

# クリーンアップ
kubectl delete pod netpol-test -n manaos-production
```

---

### 3. RBAC & ServiceAccounts（最小権限の原則）

各サービスに専用 ServiceAccount を割り当て、必要最小限の権限のみ付与します。

#### 適用方法

```bash
# RBAC と ServiceAccount の適用
kubectl apply -f kubernetes/security/rbac-service-accounts.yaml
```

#### ServiceAccount 一覧

| **ServiceAccount** | **権限** | **用途** |
|-------------------|---------|---------|
| `unified-api-sa` | ConfigMap/Secret 読取、Service Discovery | Unified API |
| `mrl-memory-sa` | ConfigMap/Secret（限定）読取 | MRL Memory |
| `learning-system-sa` | ConfigMap/Secret（限定）読取 | Learning System |
| `llm-routing-sa` | ConfigMap/Secret（限定）読取 | LLM Routing |
| `prometheus-sa` | Cluster-wide 読取（メトリクス用） | Prometheus |
| `github-actions-sa` | Deployment 管理 | CI/CD パイプライン |
| `velero-sa` | Cluster-wide 全権限（バックアップ用） | Velero Backup |

#### ロール階層

| **ロール** | **権限レベル** | **対象者** |
|-----------|--------------|-----------|
| `sre-full-access` | Cluster Admin | SRE チーム |
| `security-auditor` | Read-Only（全リソース） | セキュリティチーム |
| `developer-readonly` | Read-Only（アプリリソース） | 開発者（本番） |
| `edit`（Built-in） | 編集権限 | 開発者（開発環境） |

#### Deployment での使用例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unified-api
  namespace: manaos-production
spec:
  template:
    spec:
      serviceAccountName: unified-api-sa  # 専用 SA を指定
      containers:
      - name: api
        image: manaos/unified-api:latest
        # ...
```

---

### 4. セキュリティスキャン自動化

CI/CD パイプライン内でセキュリティスキャンを自動化します。

#### 適用方法

```bash
# セキュリティスキャン設定の適用
kubectl apply -f kubernetes/security/security-scanning.yaml

# GitHub Actions ワークフローをコピー
# .github/workflows/security-scan.yml として保存
```

#### スキャンの種類

| **スキャンタイプ** | **ツール** | **対象** | **実行タイミング** |
|-------------------|-----------|---------|------------------|
| **SAST** | Semgrep, Bandit | ソースコード | Push/PR/毎日 |
| **依存関係** | Safety, pip-audit, OWASP | requirements.txt | Push/PR/毎日 |
| **コンテナ** | Trivy | Docker Image | ビルド時/毎日 |
| **シークレット** | TruffleHog, GitLeaks | Git履歴 | Push/PR |
| **IaC** | Kubesec, Checkov | Kubernetes YAML | Push/PR |
| **ライセンス** | pip-licenses | 依存パッケージ | PR |
| **ランタイム** | Trivy Operator | デプロイ済みPod | 毎日3AM |

#### ローカル開発でのスキャン

```bash
# Pre-commit フックのインストール
pip install pre-commit
pre-commit install

# 手動スキャン
pre-commit run --all-files

# 個別スキャン
semgrep --config=p/security-audit .
trivy image manaos/unified-api:latest
safety check
trufflehog git file://. --since-commit HEAD
```

#### 脆弱性対応 SLA

| **深刻度** | **CVSS スコア** | **対応期限** | **承認者** |
|-----------|----------------|-------------|-----------|
| **Critical** | 9.0-10.0 | 24時間 | セキュリティチーム |
| **High** | 7.0-8.9 | 7日 | エンジニアリングマネージャー |
| **Medium** | 4.0-6.9 | 30日 | チームリード |
| **Low** | 0.1-3.9 | ベストエフォート | - |

---

## バックアップ・災害対策

### Velero バックアップ設定

Velero を使用して、Kubernetes クラスタの自動バックアップと災害復旧を実現します。

#### Velero インストール

```bash
# Velero CLI のインストール（macOS）
brew install velero

# Velero CLI のインストール（Linux）
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# AWS 認証情報の準備
cat > credentials-velero <<EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
EOF

# Velero のインストール
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket manaos-velero-backups \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero \
  --use-volume-snapshots=true

# バックアップスケジュールの適用
kubectl apply -f kubernetes/backup/velero-config.yaml
```

#### バックアップスケジュール

| **スケジュール名** | **頻度** | **対象** | **保持期間** |
|------------------|---------|---------|------------|
| `hourly-critical-backup` | 毎時0分 | Critical ラベル付きリソース | 7日 |
| `daily-production-backup` | 毎日2AM | Production Namespace | 30日 |
| `weekly-full-backup` | 毎週日曜3AM | 全 Namespace | 90日 |
| `monthly-archive-backup` | 毎月1日4AM | 全 Namespace | 1年 |

#### 災害復旧手順

**1. 新しいクラスタに Velero をインストール**

```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket manaos-velero-backups \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero
```

**2. 利用可能なバックアップを確認**

```bash
velero backup get
```

**3. リストアの実行**

```bash
# 完全リストア
velero restore create --from-backup daily-production-backup-20260215020000

# リストア状況の確認
velero restore describe production-disaster-recovery
velero restore logs production-disaster-recovery
```

**4. アプリケーションの検証**

```bash
# Pod の確認
kubectl get pods -n manaos-production

# サービスの疎通確認
kubectl port-forward -n manaos-production svc/unified-api 9510:9510
curl http://localhost:9510/health
```

#### バックアップのテスト（推奨：月次実施）

```bash
# 1. テスト用 Namespace を作成
kubectl create namespace dr-test

# 2. テスト用 Namespace にリストア
velero restore create dr-test-restore \
  --from-backup daily-production-backup-latest \
  --namespace-mappings manaos-production:dr-test

# 3. アプリケーションの動作確認
kubectl -n dr-test get pods
kubectl -n dr-test port-forward svc/unified-api 9510:9510

# 4. クリーンアップ
kubectl delete namespace dr-test
```

---

## オブザーバビリティ

### 1. Jaeger 分散トレーシング

マイクロサービス間のリクエストフローを可視化し、ボトルネックを特定します。

#### Jaeger のデプロイ

```bash
# Jaeger と OpenTelemetry Collector のデプロイ
kubectl apply -f kubernetes/observability/jaeger-tracing.yaml

# Jaeger UI へのアクセス
kubectl port-forward -n tracing svc/jaeger-query 16686:16686

# ブラウザで開く: http://localhost:16686
```

#### アプリケーションへの OpenTelemetry 追加

**1. 依存関係のインストール**

```bash
pip install opentelemetry-api \
            opentelemetry-sdk \
            opentelemetry-instrumentation-fastapi \
            opentelemetry-instrumentation-requests \
            opentelemetry-instrumentation-redis \
            opentelemetry-instrumentation-psycopg2 \
            opentelemetry-exporter-otlp
```

**2. トレーシングのセットアップ**

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# トレーサープロバイダーの設定
resource = Resource.create({"service.name": "unified-api"})
tracer_provider = TracerProvider(resource=resource)

# OTLP Exporter の設定
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector.tracing.svc.cluster.local:4317",
    insecure=True,
)

span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

# FastAPI の自動計装
FastAPIInstrumentor.instrument()

# カスタムスパンの作成
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom-operation") as span:
    span.set_attribute("user.id", user_id)
    # 処理...
```

#### トレースの検索方法

- **サービス名で検索**: `unified-api`, `mrl-memory`, `learning-system`
- **オペレーション名で検索**: `/api/v1/memory/store`, `/api/v1/llm/route`
- **タグで検索**: `user.id=12345`, `http.status_code=500`
- **レイテンシで検索**: `duration > 1s`

---

### 2. Loki ログ集約

Grafana Loki を使用して、すべてのマイクロサービスのログを一元管理します。

#### Loki のデプロイ

```bash
# Loki と Promtail のデプロイ
kubectl apply -f kubernetes/observability/loki-logging.yaml

# Loki への接続確認
kubectl port-forward -n monitoring svc/loki 3100:3100
curl http://localhost:3100/ready
```

#### Grafana でのログ表示

**1. Loki データソースの追加**

```bash
# Grafana にアクセス
kubectl port-forward -n monitoring svc/grafana 3000:3000

# ブラウザで開く: http://localhost:3000
# Configuration → Data Sources → Add data source → Loki
# URL: http://loki:3100
```

**2. LogQL クエリの例**

```logql
# Production Namespace のすべてのログ
{namespace="manaos-production"}

# エラーログのみ
{namespace="manaos-production"} |= "ERROR"

# 特定アプリのログ
{namespace="manaos-production", app="unified-api"}

# JSON ログをパース
{app="unified-api"} | json | level="ERROR"

# エラー率の計算
sum(rate({namespace="manaos-production"} |= "ERROR" [5m])) by (app)

# レスポンスタイムの平均
avg_over_time({app="unified-api"} | json | unwrap response_time [5m])

# 特定 Trace の検索
{namespace="manaos-production"} | json | trace_id="abc123def456"
```

#### ログアラートの設定

アラートルールは自動的に適用されます：

- **HighErrorRate**: エラー率が 10/sec を超えた場合
- **CriticalErrors**: Critical ログが検出された場合
- **DatabaseConnectionErrors**: DB接続エラーが 5/min を超えた場合
- **OOMKillDetected**: Pod が OOM Kill された場合
- **HighAuthenticationFailures**: 認証失敗が 20/sec を超えた場合

---

## クイックスタート

### ステップ1: セキュリティ設定の適用

```bash
# 1. Pod Security Standards
kubectl apply -f kubernetes/security/pod-security-standards.yaml

# 2. Network Policies
kubectl apply -f kubernetes/security/network-policies.yaml

# 3. RBAC & ServiceAccounts
kubectl apply -f kubernetes/security/rbac-service-accounts.yaml

# 4. セキュリティスキャン設定
kubectl apply -f kubernetes/security/security-scanning.yaml
```

### ステップ2: バックアップの設定

```bash
# Velero のインストールと設定
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket manaos-velero-backups \
  --backup-location-config region=us-west-2 \
  --secret-file ./credentials-velero

# バックアップスケジュールの適用
kubectl apply -f kubernetes/backup/velero-config.yaml
```

### ステップ3: オブザーバビリティの設定

```bash
# Jaeger のデプロイ
kubectl apply -f kubernetes/observability/jaeger-tracing.yaml

# Loki のデプロイ
kubectl apply -f kubernetes/observability/loki-logging.yaml
```

### ステップ4: 動作確認

```bash
# セキュリティ設定の確認
kubectl get namespaces --show-labels
kubectl get networkpolicies -A
kubectl get serviceaccounts -n manaos-production

# バックアップの確認
velero backup get
velero schedule get

# オブザーバビリティの確認
kubectl get pods -n tracing
kubectl get pods -n monitoring -l app=loki
kubectl get pods -n monitoring -l app=promtail
```

---

## 運用ベストプラクティス

### セキュリティ

1. **Pod Security Standards**: 本番環境は Restricted プロファイルを使用
2. **Network Policies**: デフォルト拒否からスタート
3. **RBAC**: 最小権限の原則を徹底
4. **セキュリティスキャン**: CI/CD に統合し、Critical 脆弱性はブロック
5. **Secret 管理**: Sealed Secrets または External Secrets Operator を使用
6. **監査ログ**: Kubernetes 監査ログを有効化

### バックアップ

1. **3-2-1 ルール**: 3つのコピー、2つの異なるメディア、1つはオフサイト
2. **定期的なリストアテスト**: 月次で DR 訓練を実施
3. **バックアップ検証**: CronJob で自動検証
4. **アップグレード前**: 必ず手動バックアップを取得
5. **保持期間**: 法規制に準拠した保持期間を設定

### オブザーバビリティ

1. **ログ構造化**: JSON 形式でログ出力（パース可能）
2. **トレース ID 付与**: すべてのログに trace_id を含める
3. **メトリクス4つの黄金シグナル**: レイテンシ、トラフィック、エラー、飽和度
4. **アラート**: ノイズを減らし、アクション可能なアラートのみ設定
5. **ダッシュボード**: サービスごとに SLI/SLO ダッシュボードを作成

### 監視項目

| **カテゴリ** | **監視項目** | **しきい値** |
|------------|------------|------------|
| **アプリケーション** | エラー率 | > 5% |
| **アプリケーション** | レスポンスタイム | > 1s |
| **インフラ** | CPU 使用率 | > 80% |
| **インフラ** | メモリ使用率 | > 80% |
| **インフラ** | ディスク使用率 | > 85% |
| **セキュリティ** | 認証失敗 | > 20/sec |
| **セキュリティ** | 脆弱性 | Critical 検出 |
| **バックアップ** | バックアップ失敗 | 1回でも失敗 |

---

## トラブルシューティング

### Pod Security Standards エラー

**エラー**: `pods "xxx" is forbidden: violates PodSecurity "restricted:latest"`

**解決策**:
1. Pod の SecurityContext を確認
2. `runAsNonRoot: true` を設定
3. すべての Capabilities をドロップ
4. `readOnlyRootFilesystem: true` を設定
5. Resource limits を設定

### Network Policy で通信できない

**確認手順**:
```bash
# NetworkPolicy の確認
kubectl get networkpolicies -n manaos-production
kubectl describe networkpolicy <policy-name> -n manaos-production

# Pod のラベル確認
kubectl get pods -n manaos-production --show-labels

# テスト用 Pod から疎通確認
kubectl exec -n manaos-production netpol-test -- curl -I http://target-service:8080
```

### Velero バックアップが失敗する

**確認手順**:
```bash
# バックアップ詳細の確認
velero backup describe <backup-name>
velero backup logs <backup-name>

# Velero Pod のログ確認
kubectl logs -n velero deploy/velero

# S3 バケットへのアクセス確認
kubectl exec -n velero deploy/velero -- aws s3 ls s3://manaos-velero-backups
```

### Jaeger にトレースが表示されない

**確認手順**:
```bash
# OpenTelemetry Collector のログ確認
kubectl logs -n tracing deploy/otel-collector

# Jaeger Collector のログ確認
kubectl logs -n tracing deploy/jaeger-all-in-one

# アプリケーションから OTLP Exporter への接続確認
kubectl exec -n manaos-production <pod-name> -- nslookup otel-collector.tracing.svc.cluster.local
```

### Loki にログが表示されない

**確認手順**:
```bash
# Promtail のログ確認
kubectl logs -n monitoring daemonset/promtail

# Loki のログ確認
kubectl logs -n monitoring statefulset/loki

# Promtail から Loki への接続確認
kubectl exec -n monitoring <promtail-pod> -- curl -I http://loki:3100/ready
```

---

## まとめ

本ガイドで実装した機能により、ManaOS プラットフォームは以下のエンタープライズグレードの要件を満たします：

✅ **セキュリティ**: Pod Security Standards, Network Policies, RBAC, 自動スキャン  
✅ **信頼性**: 自動バックアップ、災害復旧手順、定期的なリストアテスト  
✅ **可観測性**: 分散トレーシング、ログ集約、メトリクス監視  
✅ **コンプライアンス**: 監査ログ、ライセンス管理、脆弱性管理  
✅ **運用性**: 自動化、CI/CD 統合、アラート設定  

これらの設定により、本番環境での安全で信頼性の高い運用が可能になります。

---

## 関連ドキュメント

- [Complete Deployment Guide](COMPLETE_DEPLOYMENT_GUIDE.md) - 全デプロイメントシナリオ
- [Kubernetes Deployment](KUBERNETES_DEPLOYMENT.md) - Kubernetes 基本デプロイ
- [ArgoCD GitOps Guide](ARGOCD_GITOPS_GUIDE.md) - GitOps による自動デプロイ
- [Testing Guide](TESTING_GUIDE.md) - テスト実行方法
- [Security Hardening](docs/guides/SECURITY_HARDENING.md) - API セキュリティ

---

**最終更新**: 2026-02-16  
**バージョン**: 1.0.0  
**著者**: ManaOS Platform Team
