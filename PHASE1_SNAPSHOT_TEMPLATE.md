# Phase 1 (Read-only) スナップショット共有テンプレート

## 📋 共有方法

Phase 1を起動したら、以下を共有してください：

### 方法1: JSONスナップショット（推奨）

```bash
# スナップショットを取得
python phase1_metrics_snapshot.py phase1_metrics_snapshot.json

# JSONの内容を貼り付け
```

**例**:
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

### 方法2: 簡易形式（手動入力用）

```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
p95=0.012, gate=34%, contradiction=2%, variance=1.18, writes/min=0
```

---

## 🎯 判定結果

共有された情報に基づいて、以下を即座に判定します：

- **Go / 設定ミス / 止めるべき**
- どこを直すべきか
- Phase 2へ進む条件の最終確認

---

## 📊 判定基準（簡易版）

### SECURITY設定

- ✅ **Go**: すべてenabled
- ❌ **No-Go**: 1つでもdisabled

### E2E p95

- ✅ **Go**: < 0.1秒
- ⚠️ **注意**: 0.1〜0.3秒
- ❌ **No-Go**: > 0.3秒

### ゲート遮断率

- ✅ **Go**: 0〜80%
- ⚠️ **注意**: 80〜95%
- ❌ **No-Go**: 95〜100%

### 矛盾検出率

- ✅ **Go**: < 5%
- ⚠️ **注意**: 5〜10%
- ❌ **No-Go**: > 10%

### スロット使用率の分散

- ✅ **Go**: < 100
- ⚠️ **注意**: 100〜1000
- ❌ **No-Go**: > 1000

### 書き込み回数/分

- ✅ **Go**: 0
- ❌ **No-Go**: > 0（Read-onlyなのに書き込みが発生）

### ストレージ（健康診断）

- ✅ **Go**: ベースラインと比較して行数が増えていない
- ❌ **No-Go**: Read-onlyモードなのに行数が増えている

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1スナップショット共有テンプレート確定
