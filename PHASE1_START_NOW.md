# Phase 1 (Read-only) 開始手順（今すぐ実行）

## 🚀 Phase 1 起動手順（順番そのまま）

### 1. Preflight（デプロイ前の最終チェック）

```bash
python phase1_preflight_check.py
```

**すべてのチェックがパスすることを確認**

---

### 2. 起動

#### systemdの場合

```bash
# サービスファイルをコピー（パスを編集してから）
sudo cp mrl-memory.service /etc/systemd/system/
sudo nano /etc/systemd/system/mrl-memory.service  # パスを編集

# サービスを起動
sudo systemctl daemon-reload
sudo systemctl start mrl-memory

# ステータス確認
sudo systemctl status mrl-memory
```

#### PM2の場合

```bash
pm2 start ecosystem.config.js

# ステータス確認
pm2 status
```

#### 直接起動の場合（テスト用）

```bash
# 環境変数を設定
export $(cat .env | xargs)

# 起動
python mrl_memory_integration.py
```

**起動ログに以下が表示されることを確認**:
```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
✅ Rollout Manager初期化: enabled=True, write_mode=readonly, ...
```

---

### 3. 疎通確認

```bash
python phase1_connectivity_test.py
```

**4つのテストがすべてパスすることを確認**:
- [ ] 認証なし → 401
- [ ] 認証あり → 200
- [ ] MAX_INPUT超過 → 413/400
- [ ] レート超過 → 429

---

### 4. スナップショット取得（開始時）

```bash
python phase1_metrics_snapshot.py phase1_metrics_snapshot_baseline.json
```

**出力されたJSONをコピー**

---

### 5. 健康診断（Read-onlyの裏取り）

```bash
python phase1_health_check.py
```

**結果を確認**

---

### 6. 自動判定

```bash
python phase1_decision_maker.py phase1_metrics_snapshot_baseline.json
```

**判定結果を確認**

---

## 📋 ここに貼ってほしいもの（最小）

### 方法1: JSONスナップショット（推奨）

`phase1_metrics_snapshot_baseline.json` の中身（全部）

**例**:
```json
{
  "timestamp": "2026-01-15T00:00:00",
  "phase": "Phase 1: Read-only",
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

### 方法2: 判定結果の要点

- `phase1_decision_maker.py` の判定結果（1行）
- `phase1_health_check.py` の結果（要点）

---

## 🎯 判定の型（先に置いておく）

### Go判定の例

以下の条件を満たす場合：

- `writes_per_min=0` ✅（Read-onlyの最重要）
- `auth/rate_limit/pii_mask enabled` ✅（本番セキュア）
- `p95 < 0.1秒` ✅（余裕、問題なし）
- `gate_block_rate 0〜80%` ✅（使われてる）
- `contradiction_rate < 5%` ✅（低く安定ならOK）
- `slot_usage_variance < 100` ✅（極端な偏りじゃなさそう）

→ **Go（Phase 1継続）**
→ 24〜48h安定したら Phase 2へ

---

## ⚠️ 自動判定がGoでも止めるケース（例外ルール）

自動判定がGoでも、次があれば止める判定に寄せる：

- ❌ 5xxが増えてる（60分で複数）
- ❌ Read-onlyなのに永続化ストアの行数が増える（健康診断で検出）
- ❌ ゲート遮断率が時間とともに95%に張り付く（メモリ参照が害化）
- ❌ 矛盾検出率が右肩上がり（入力が汚い or 判定が過敏）

---

## 📝 チェックリスト

### 起動前

- [ ] `.env`ファイルが設定されている
- [ ] `REQUIRE_AUTH=1`が設定されている
- [ ] `API_KEY`が強力なキーに設定されている
- [ ] `RATE_LIMIT_PER_MIN`が適切に設定されている
- [ ] `MAX_INPUT_CHARS`が適切に設定されている
- [ ] `FWPKM_WRITE_MODE=readonly`
- [ ] `FWPKM_REVIEW_EFFECT=0`
- [ ] `FWPKM_ENABLED=1`
- [ ] `FWPKM_WRITE_ENABLED=0`

### 起動時

- [ ] 起動ログに`SECURITY: auth=enabled, ...`が表示される
- [ ] ヘルスチェックが正常（`curl http://localhost:5105/health`）

### 疎通確認

- [ ] 認証なし → 401
- [ ] 認証あり → 200
- [ ] MAX_INPUT超過 → 413/400
- [ ] レート超過 → 429

### スナップショット取得

- [ ] `phase1_metrics_snapshot_baseline.json`が作成された
- [ ] JSONの内容を確認

### 健康診断

- [ ] ストレージの健康状態が正常
- [ ] TTLマネージャが正常に動作
- [ ] Read-onlyモードで書き込みが発生していない

### 自動判定

- [ ] 判定結果を確認
- [ ] Go/No-Go判定を確定

---

## 🎯 次のアクション

Phase 1を起動したら、以下を共有してください：

1. **JSONスナップショット**（`phase1_metrics_snapshot_baseline.json`の中身）
2. **自動判定結果**（`phase1_decision_maker.py`の出力）
3. **健康診断結果**（`phase1_health_check.py`の要点）

これらに基づいて、以下を即座に判定します：

- **Go / 設定ミス / 止めるべき**
- どこを直すべきか
- Phase 2へ進む条件の最終確認

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1開始準備完了
