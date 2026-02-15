# ManaOS バックアップ＆ディザスタリカバリー戦略

## 📋 概要

ビジネス継続性を確保するための包括的なバックアップと災害復旧計画です。

---

## 🔄 バックアップ戦略

### 3-2-1 ルール

```
✅ オリジナルデータ: 1コピー
✅ バックアップ: 2コピー（異なるメディア）
✅ オフサイト: 1コピー（地理的に離れた場所）
```

### バックアップタイプ

| タイプ | 頻度 | 保持期間 | 対象 |
|-------|------|---------|------|
| フル | 週1回 | 4週 | すべてのデータ |
| 差分 | 日1回 | 7日 | 変更データのみ |
| トランザクションログ | 時1回 | 24時間 | DB トランザクション |
| スナップショット | 6時間 | 48時間 | ディスク/ボリューム |

---

## 🛠️ バックアップ実装

### 1. Kubernetesリソースバックアップ

```bash
# Velero インストール
helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
helm install velero vmware-tanzu/velero \
  --namespace velero \
  --create-namespace \
  --set configuration.backupStorageLocation.bucket=manaos-backups \
  --set configuration.backupStorageLocation.provider=aws

# 定期バックアップスケジュール
cat << EOF | kubectl apply -f -
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: manaos-daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 毎日 UTC 2:00
  template:
    ttl: "720h"
    includedNamespaces:
    - manaos
    storageLocation: default
    volumeSnapshotLocation: default
EOF

# バックアップ確認
velero backup get

# リストア
velero restore create --from-backup manaos-daily-backup-20260216
```

### 2. ボリュームスナップショット

```bash
# VolumeSnapshotClass 作成
cat << EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: manaos-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
EOF

# スナップショット定義
cat << EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: manaos-data-snapshot
  namespace: manaos
spec:
  volumeSnapshotClassName: manaos-snapshots
  source:
    persistentVolumeClaimName: unified-api-data
EOF
```

### 3. データベースバックアップ

```bash
# Postgres バックアップ
PGPASSWORD=password pg_dump -h postgres-host -U manaos_user manaos_db | \
  gzip > manaos-db-$(date +%Y%m%d-%H%M%S).sql.gz

# 暗号化して S3 へアップロード
openssl enc -aes-256-cbc -salt -in manaos-db-*.sql.gz \
  -out manaos-db-encrypted.sql.gz.enc -k $BACKUP_KEY

aws s3 cp manaos-db-encrypted.sql.gz.enc s3://manaos-backups/db/
```

### 4. アプリケーションデータバックアップ

```bash
# Redis バックアップ
redis-cli BGSAVE

# Redis スナップショップをS3へアップロード
aws s3 cp /var/lib/redis/dump.rdb s3://manaos-backups/redis/

# Registry バックアップ
tar czf manaos-registry-$(date +%Y%m%d).tar.gz /var/lib/registry/

aws s3 cp manaos-registry-*.tar.gz s3://manaos-backups/registry/
```

---

## 🚨 ディザスタリカバリー計画

### RTO/RPO目標

| リソース | RTO | RPO | 説明 |
|---------|-----|-----|------|
| API Service | 15分 | 5分 | クリティカル |
| Memory Cache | 30分 | 1時間 | 重要 |
| Learning DB | 1時間 | 30分 | 重要 |
| 静止画像 | 4時間 | 1日 | 低優先度 |

### レベル別リカバリー手順

#### レベル1: サービス障害（単一Pod）

```bash
# 障害Pod削除→自動再起動
kubectl delete pod unified-api-xxx -n manaos

# または HPA に任せる
kubectl get hpa -n manaos
```

#### レベル2: ノード障害

```bash
# ノードの Drain
kubectl drain node-name --ignore-daemonsets

# Karpenter/ClusterAutoscaler が新ノード起動
kubectl get nodes -L node.kubernetes.io/capacity-type

# Workload の自動再スケジュール
kubectl get events -n manaos --sort-by='.lastTimestamp'
```

#### レベル3: クラスタ部分障害

```bash
# ネットワークパーティション
# -> ClusterIP Service に問題がないか確認
kubectl exec -it pod-name -n manaos -- ping svc.cluster.local

# DNS キャッシュ削除
kubectl rollout restart deployment/coredns -n kube-system
```

#### レベル4: クラスタ全体障害

```bash
# CertificateSigningRequest キャッシュクリア
kubectl delete csr --all

# 別クラスタへの復旧
velero restore create --from-backup manaos-daily-backup-20260216 \
  --restore-volumes=true
```

#### レベル5: 複数リージョン障害

```
リージョン1（プライマリ） ----X---- リージョン2（セカンダリ）

アクション：
1. Route53 フェイルオーバー有効化
2. セカンダリリージョンへトラフィック切替
3. 最新バックアップからリストア
```

---

## 🔐 バックアップセキュリティ

### 暗号化

```bash
# 転送中の暗号化（HTTPS）
aws s3 cp file.tar.gz s3://bucket/ --sse AES256

# 保存時の暗号化
aws s3api put-bucket-encryption \
  --bucket manaos-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### アクセス制御

```bash
# IAM ポリシー（最小権限）
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/velero"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::manaos-backups/*"
    }
  ]
}
```

### 監査ログ

```bash
# S3 バージョニング有効化
aws s3api put-bucket-versioning \
  --bucket manaos-backups \
  --versioning-configuration Status=Enabled

# MFA削除有効化
aws s3api put-bucket-versioning \
  --bucket manaos-backups \
  --versioning-configuration Status=Enabled,MFADelete=Enabled
```

---

## 🧪 バックアップテスト

### リストアテスト計画

```bash
# 月1回のフルリストアテスト
# 開発環境で実行
velero restore create \
  --from-backup manaos-daily-backup-20260214 \
  --restore-volumes=true \
  --namespace-mappings manaos:manaos-test

# データ整合性チェック
kubectl run restore-validator \
  --image=manaos/restore-validator:latest \
  -n manaos-test \
  -- validate-restore.sh
```

### RPO/RTO 検証

```bash
#!/bin/bash
# rpo_rto_test.sh

# バックアップ作成時刻
BACKUP_TIME=$(date -d "$(velero backup describe manaos-daily-backup | grep 'Created:' | awk '{print $2, $3}' )"  +%s)

# 現在時刻
CURRENT_TIME=$(date +%s)

# RPO（目標15分）
RPO_SECONDS=$((15 * 60))
ACTUAL_RPO=$((CURRENT_TIME - BACKUP_TIME))

if [ $ACTUAL_RPO -lt $RPO_SECONDS ]; then
  echo "✅ RPO OK: ${ACTUAL_RPO}s < ${RPO_SECONDS}s"
else
  echo "❌ RPO VIOLATION: ${ACTUAL_RPO}s > ${RPO_SECONDS}s"
fi

# RTO（目標15分）
RESTORE_START=$(date +%s)
velero restore create --from-backup manaos-daily-backup
# ... リストア完了まで待機 ...
RESTORE_END=$(date +%s)

ACTUAL_RTO=$((RESTORE_END - RESTORE_START))
RTO_SECONDS=$((15 * 60))

if [ $ACTUAL_RTO -lt $RTO_SECONDS ]; then
  echo "✅ RTO OK: ${ACTUAL_RTO}s < ${RTO_SECONDS}s"
else
  echo "❌ RTO VIOLATION: ${ACTUAL_RTO}s > ${RTO_SECONDS}s"
fi
```

---

## 📊 監視とアラート

```yaml
# Prometheus アラートルール
groups:
  - name: backup-alerts
    rules:
      - alert: BackupFailure
        expr: velero_backup_last_status{status!="Completed"} == 1
        for: 1h
        annotations:
          summary: "Backup failed"
      
      - alert: BackupAge
        expr: (time() - velero_backup_last_successful_timestamp) / 3600 > 25
        annotations:
          summary: "Backup is older than 24 hours"
      
      - alert: RestoreFailure
        expr: velero_restore_last_status{status!="Completed"} == 1
        annotations:
          summary: "Restore failed"
```

---

## 📋 チェックリスト

- [ ] バックアップスケジュール設定済み
- [ ] オフサイトストレージ契約済み
- [ ] 暗号化キー安全に保管
- [ ] 月1回のリストアテスト実施
- [ ] RPO/RTO 目標達成確認
- [ ] ディザスタリカバリー計画を全チーム共有
- [ ] セキュリティ監査完了
- [ ] 保有期間ポリシー設定
- [ ] コスト最適化検討

---

## 🔗 関連ドキュメント

- [Velero 公式ドキュメント](https://velero.io/docs/)
- [AWS バックアップベストプラクティス](https://aws.amazon.com/jp/backup/)
- [NIST DR ガイドライン](https://csrc.nist.gov/publications/detail/sp/800-34/rev-1/final)
