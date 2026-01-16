# Phase 1 判定テンプレート（実測値が来たら秒で判定）

## 🎯 判定の順番（固定・この順で見る）

実測JSON（baseline→warmup）が来たら、**この順番で必ずチェック**する。

---

## ① SECURITY（必須・容赦なし）

### チェック項目

- [ ] `security.auth == "enabled"` ✅
- [ ] `security.rate_limit == "enabled"` ✅
- [ ] `security.pii_mask == "enabled"` ✅
- [ ] `security.max_input` が想定値（例: 200000以上）✅

### 判定

**1個でも❌なら即「設定ミス」**

**修正箇所**:
- `auth != "enabled"` → `.env`で`REQUIRE_AUTH=1`を確認
- `rate_limit != "enabled"` → `.env`で`RATE_LIMIT_PER_MIN`が設定されているか確認
- `pii_mask != "enabled"` → `.env`で`PII_MASK_ENABLED=1`を確認
- `max_input < 200000` → `.env`で`MAX_INPUT_CHARS=200000`以上を確認

---

## ② Read-only裏取り（最重要・一発アウト）

### チェック項目

- [ ] `metrics.writes_per_min == 0` ✅
- [ ] `storage_delta.*` が全部 0 ✅（scratchpad/quarantine/promoted等）
- [ ] `config.write_mode == "readonly"` ✅
- [ ] `config.write_enabled == "0"` ✅

### 判定

**どっちか崩れたら即「設定ミス」**

Read-onlyで書いてたら、Phase 1の意味がなくなるからここは一発アウト。

**修正箇所**:
- `writes_per_min > 0` → `.env`で`FWPKM_WRITE_MODE=readonly`と`FWPKM_WRITE_ENABLED=0`を確認
- `storage_delta.* != 0` → Read-onlyなのに永続化ストアが増えている。書き込みが発生している可能性
- `config.write_mode != "readonly"` → `.env`で`FWPKM_WRITE_MODE=readonly`を確認

---

## ③ 5xx（止めどき）

### チェック項目

- [ ] `errors.http_5xx_last_60min == 0` ✅（理想）

### 判定

**目安**:
- **0** → Go
- **1〜2** → 注意（原因ログを見る）
- **3以上** → **止めるべき**（ロールアウトどころじゃない）

**修正箇所**（3以上の場合）:
- ログを確認して原因を特定
- APIサーバーのエラーログを確認
- 必要に応じてKill Switchを有効化

---

## ④ "意味のある値"が取れているか（0固定の再発チェック）

### チェック項目

- [ ] `metrics.e2e_p95_sec` が 0 じゃない（または明確に小さい値）✅
- [ ] `metrics.gate_block_rate` が全部0で貼り付いてない ✅
- [ ] `metrics.contradiction_rate` が全部0で貼り付いてない ✅
- [ ] `metrics.slot_usage_variance` が全部0で貼り付いてない ✅

### 判定

**Read-onlyでも参照が動けば普通は揺れる**

ここが怪しい場合は「**判定不能（計測経路の問題）**」扱いにして、Go/No-Goじゃなく修正に寄せる。

**修正箇所**:
- メトリクスが0固定 → ダッシュボードJSONの読み込みを確認、APIサーバーのプロセスから直接取得するか、メトリクスを永続化する

---

## ⑤ baseline → warmup での変化（いい意味で"動く"か）

### チェック項目（warmupがある場合）

- [ ] `e2e_p95_sec`：少し上がる or ほぼ同じ ✅
- [ ] `gate_block_rate`：0→適度な値に動く ✅
- [ ] `contradiction_rate`：急増しない（上がっても軽微）✅
- [ ] `storage_delta`：Read-onlyなら増えない（=0維持）✅

### 判定

**正常な変化**:
- `e2e_p95_sec`：warmupで少し上がる（負荷が乗るため）
- `gate_block_rate`：0から適度な値（例: 0.1〜0.5）に動く
- `contradiction_rate`：急増しない（上がっても軽微、例: 0.01→0.02）
- `storage_delta`：Read-onlyなら増えない（=0維持）

**異常な変化**:
- `e2e_p95_sec`：warmupで2倍以上に跳ねる → 止めるべき
- `gate_block_rate`：95%に張り付く → 止めるべき
- `contradiction_rate`：急増（例: 0.01→0.10）→ 止めるべき
- `storage_delta`：Read-onlyなのに増える → 設定ミス

---

## 🎯 最終判定（3択）

### Go（Phase 1継続）

**条件**:
- ① SECURITY: すべて✅
- ② Read-only裏取り: すべて✅
- ③ 5xx: 0（または1〜2で原因が明確で対処済み）
- ④ 意味のある値: すべて✅
- ⑤ baseline→warmup: 正常な変化（またはwarmupなし）

**次のステップ**:
- Phase 1を24〜48時間継続
- 定期的にダッシュボードを確認
- Phase 2 Go条件を満たしたらPhase 2へ

---

### 設定ミス（即修正）

**条件**:
- ① SECURITY: 1個でも❌
- ② Read-only裏取り: どっちか崩れた

**修正箇所**（1〜3点に絞って提示）:
1. `.env`で`REQUIRE_AUTH=1`を確認
2. `.env`で`FWPKM_WRITE_MODE=readonly`を確認
3. `.env`で`FWPKM_WRITE_ENABLED=0`を確認

**次のステップ**:
- 修正後に再起動
- 再度baselineスナップショットを取得
- 再判定

---

### 止めるべき（即停止）

**条件**:
- ③ 5xx: 3以上
- ⑤ baseline→warmup: 異常な変化（p95爆増、矛盾率暴走など）

**原因**（1〜3点に絞って提示）:
1. 5xxエラーが増加（ログを確認）
2. p95が急増（前回比2倍以上）
3. 矛盾検出率が暴走（急増）

**次のステップ**:
- Kill Switchを有効化（`FWPKM_ENABLED=0`）
- ログを確認して原因を特定
- 修正後に再起動
- 再度baselineスナップショットを取得
- 再判定

---

## 📋 判定不能（計測経路の問題）

**条件**:
- ④ 意味のある値: 怪しい（0固定など）

**次のステップ**:
- メトリクスの取得経路を確認
- ダッシュボードJSONの読み込みを確認
- APIサーバーのプロセスから直接取得するか、メトリクスを永続化する
- 修正後に再判定

---

## ⚠️ 注意事項

### Phase 1 "Read-only" の定義

**FWPKMが書かない**だけじゃなく、**RAGや他の層が副作用で書かない**ことも含む場合がある。

`storage_delta`の対象に**RAG側の永続ストア**も入ってるか（or 別途監視してるか）が、もし抜けてたら後で追加した方がいい。

（今すぐ必須ではない、でも後で刺さる可能性はある）

---

## 📊 判定結果のフォーマット

実測JSONが来たら、以下のフォーマットで返す：

```markdown
## Phase 1 判定結果

### ① SECURITY
- auth: ✅/❌
- rate_limit: ✅/❌
- pii_mask: ✅/❌
- max_input: ✅/❌（値: ___）

### ② Read-only裏取り
- writes_per_min: ___（期待: 0）✅/❌
- storage_delta: ___（期待: 0）✅/❌
- config.write_mode: ___（期待: readonly）✅/❌

### ③ 5xx
- http_5xx_last_60min: ___

### ④ 意味のある値
- e2e_p95_sec: ___ ✅/❌
- gate_block_rate: ___ ✅/❌
- contradiction_rate: ___ ✅/❌

### ⑤ baseline→warmup変化
- e2e_p95_sec: baseline=___ → warmup=___ ✅/❌
- gate_block_rate: baseline=___ → warmup=___ ✅/❌
- contradiction_rate: baseline=___ → warmup=___ ✅/❌
- storage_delta: baseline=___ → warmup=___ ✅/❌

### 結論
**Go / 設定ミス / 止めるべき**

### 修正箇所（最大3つ）
1. ...
2. ...
3. ...

### Phase 2へ進む条件
- 24〜48h安定（p95スパイクなし、5xxなし）
- 矛盾率急増なし
- ゲート遮断率が95%貼り付きなし
- Read-onlyの裏取りが維持（writes=0＆永続化増加なし）
```

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: 判定テンプレート確定
