# Phase 1 (Read-only) 運用ルーチン

## 📋 Phase 1開始後の運用ルーチン（超短い）

### 1. デプロイ前の最終チェック

```bash
python phase1_preflight_check.py
```

### 2. 起動

```bash
# systemd/PM2で起動
sudo systemctl start mrl-memory
# または
pm2 start ecosystem.config.js
```

### 3. 疎通確認

```bash
python phase1_connectivity_test.py
```

### 4. スナップショット取得（開始時）

```bash
# JSON形式でスナップショットを取得
python phase1_metrics_snapshot.py phase1_metrics_snapshot_baseline.json

# または、ダッシュボードから取得
python mrl_memory_dashboard.py --json phase1_metrics_snapshot_baseline.json
```

### 5. Go/No-Go判定

```bash
# JSONスナップショットから自動判定
python phase1_decision_maker.py phase1_metrics_snapshot_baseline.json

# または、手動入力モード
python phase1_decision_maker.py
```

### 6. ロールアウトログに記録

`MRL_MEMORY_ROLLOUT_LOG.md`に以下を記録：

- 開始日時
- SECURITYログ1行
- ダッシュボード初期値（JSONスナップショットを貼り付け）

---

## 📊 定期的な確認（24時間ごと）

### 1. スナップショット取得

```bash
python phase1_metrics_snapshot.py phase1_metrics_snapshot.json
```

### 2. 健康診断

```bash
python phase1_health_check.py
```

### 3. スナップショット比較

```bash
# ベースラインと比較（Read-onlyモードで書き込みが発生していないか）
python phase1_health_check.py
```

### 4. ロールアウトログに記録

`MRL_MEMORY_ROLLOUT_LOG.md`に以下を記録：

- 日時
- 各指標の値（JSONスナップショットを貼り付け）
- 異常があれば内容と対応

---

## 🔍 健康診断の内容

### 1. ストレージの健康状態

- Scratchpadの行数
- Quarantineの行数
- Promotedの行数

### 2. TTLマネージャの動作確認

- 期限切れエントリの削除が正常に動作しているか

### 3. スナップショット比較

- Read-onlyモードで書き込みが発生していないか
- ベースラインと比較して、行数が増えていないか

---

## 📝 スナップショットのフォーマット

### JSON形式（固定）

```json
{
  "timestamp": "2026-01-15T00:00:00",
  "phase": "readonly",
  "security": {
    "auth": "enabled",
    "rate_limit": "enabled",
    "max_input": 200000,
    "pii_mask": "enabled"
  },
  "metrics": {
    "e2e_p95_sec": 0.012,
    "gate_block_rate": 0.34,
    "contradiction_rate": 0.02,
    "slot_usage_variance": 1.18,
    "writes_per_min": 0
  },
  "storage": {
    "scratchpad_entries": 100,
    "quarantine_entries": 5,
    "promoted_entries": 10
  },
  "errors": {
    "http_5xx_last_60min": 0
  }
}
```

### キー名の定義（固定）

- `e2e_p95_sec`: E2E p95（秒）
- `gate_block_rate`: ゲート遮断率（0.0-1.0）
- `contradiction_rate`: 矛盾検出率（0.0-1.0）
- `slot_usage_variance`: スロット使用率の分散
- `writes_per_min`: 書き込み回数/分

**このキー名は変更しないでください**（判定スクリプトが依存しています）

---

## 🚀 Phase 2 Go条件の確認（24〜48時間後）

```bash
# スナップショットを取得
python phase1_metrics_snapshot.py phase1_metrics_snapshot.json

# 健康診断
python phase1_health_check.py

# Phase 2 Go条件をチェック（手動でチェックリストを確認）
# PHASE2_GO_CONDITIONS.mdを参照
```

---

## 📋 チェックリスト（毎日）

### 朝の確認

- [ ] ダッシュボードで指標を確認
- [ ] 健康診断を実行
- [ ] ログに異常がないか確認
- [ ] 停止ラインに達していないか確認

### 夜の確認

- [ ] 1日のスナップショットを取得
- [ ] 健康診断を実行
- [ ] `MRL_MEMORY_ROLLOUT_LOG.md`に記録

---

## 🆘 トラブルシューティング

### スナップショットが取得できない

→ メトリクスが初期化されていない可能性
→ ダッシュボードを実行してメトリクスを生成

### 健康診断で書き込みが検出された

→ Read-onlyモードなのに書き込みが発生
→ 設定を確認: `FWPKM_WRITE_MODE=readonly`, `FWPKM_WRITE_ENABLED=0`
→ サービスを再起動

### 判定スクリプトがエラーになる

→ JSONのキー名が正しいか確認
→ スナップショットのフォーマットを確認

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1運用ルーチン確定
