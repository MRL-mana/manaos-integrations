# Phase 1 スナップショット - 必須キー確認

## ✅ 必須キー（判定に必要）

`phase1_metrics_snapshot.py`が生成するJSONには、以下のキーがすべて含まれています：

### Security設定

- `security.auth` - "enabled" / "disabled"
- `security.rate_limit` - "enabled" / "disabled"
- `security.max_input` - 数値（推奨: 200000以上）
- `security.pii_mask` - "enabled" / "disabled"

### メトリクス

- `metrics.e2e_p95_sec` - E2E p95レイテンシ（秒）
- `metrics.gate_block_rate` - ゲート遮断率（0.0〜1.0）
- `metrics.contradiction_rate` - 矛盾検出率（0.0〜1.0）
- `metrics.slot_usage_variance` - スロット使用率の分散
- `metrics.writes_per_min` - 書き込み回数/分（Read-onlyでは0である必要がある）

### エラー

- `errors.http_5xx_last_60min` - 過去60分間の5xxエラー数

### ストレージ（参考情報）

- `storage.scratchpad_entries` - Scratchpadのエントリ数
- `storage.quarantine_entries` - Quarantineのエントリ数
- `storage.promoted_entries` - Promotedのエントリ数

---

## 📋 JSONスナップショットの例

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

---

## 🎯 判定の最重要ポイント

### Read-onlyで書き込みしてないか

- [ ] `metrics.writes_per_min == 0` ✅
- [ ] `health_check`で永続化行数増加なし ✅

**ここがズレてたら、他が全部良くても設定ミス確定**

---

## 📊 最短フォーマット（判定可能）

JSON丸ごとが一番いいけど、雑に最短で貼るならこれでも判定できる：

```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
p95=0.012, gate=0.34, contradiction=0.02, variance=1.18, writes/min=0
health_check: 永続化行数増加=NO
5xx(60min)=0
```

---

## 🔍 判定基準（参考）

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

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: 必須キー確認完了
