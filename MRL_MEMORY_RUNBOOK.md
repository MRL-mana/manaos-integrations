# MRL Memory System - 運用手順書（RUNBOOK）

## 📋 目次

1. [起動方法](#起動方法)
2. [段階的ロールアウト手順](#段階的ロールアウト手順)
3. [停止ライン（止めどきルール）](#停止ライン止めどきルール)
4. [Kill Switchの使い方](#kill-switchの使い方)
5. [障害時の切り戻し](#障害時の切り戻し)
6. [観測指標の確認方法](#観測指標の確認方法)

---

## 🚀 起動方法

### 1. 環境変数の設定

`.env.production.template`をコピーして`.env`を作成し、本番環境に合わせて設定：

```bash
cp .env.production.template .env
# .envを編集
```

**必須設定**:
- `REQUIRE_AUTH=1`（認証必須）
- `API_KEY=your_secure_api_key_here`（強力なキーを設定）
- `RATE_LIMIT_PER_MIN=60`（まずは守り固める）
- `MAX_INPUT_CHARS=200000`（128K相当でも余裕）

### 2. 起動

```bash
# 環境変数を読み込んで起動
export $(cat .env | xargs)
python mrl_memory_integration.py
```

または、systemd/pm2等で起動（後述）。

### 3. 起動確認

起動ログに以下が表示されることを確認：

```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
✅ Rollout Manager初期化: enabled=True, write_mode=readonly, ...
```

---

## 📈 段階的ロールアウト手順

### Phase 1: Read-onlyモード（1〜2日）

**目的**: メモリからの検索が正常に動作することを確認

**設定**:
```bash
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=readonly
export FWPKM_WRITE_ENABLED=0
```

**確認事項**:
- [ ] メモリからの検索が正常に動作
- [ ] 書き込みが無効化されている
- [ ] パフォーマンスに問題がない

**観測指標**:
- ゲート遮断率が極端に高すぎない（常時遮断なら無意味）
- 矛盾検出率が異常に高くない（キー設計が荒いサイン）

**停止ライン**:
- 矛盾検出率が急上昇（例：前日比2倍以上）
- ゲート遮断率が常時80%超え（メモリが汚い/無価値）

---

### Phase 2: Write 10%（1〜3日）

**目的**: 書き込みが正常に動作することを確認

**設定**:
```bash
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=sampled
export FWPKM_WRITE_SAMPLE_RATE=0.1
export FWPKM_WRITE_ENABLED=1
```

**確認事項**:
- [ ] 書き込みが正常に動作（10%のリクエストのみ）
- [ ] 書き込み回数/分が安定
- [ ] quarantine比率が暴れない（隔離が増えすぎると汚染が入ってる）

**観測指標**:
- 書き込み回数/分が安定
- quarantine比率がactiveを上回らない

**停止ライン**:
- 書き込み回数/分が想定の2倍以上に増える（暴走）
- quarantineがactiveを上回る（汚染優勢）

---

### Phase 3: Write 100%（数日）

**目的**: 全リクエストで書き込みが正常に動作することを確認

**設定**:
```bash
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=full
export FWPKM_WRITE_ENABLED=1
export FWPKM_REVIEW_EFFECT=0
```

**確認事項**:
- [ ] 全リクエストで書き込みが正常に動作
- [ ] パフォーマンスに問題がない
- [ ] メモリ使用量が正常範囲内

**観測指標**:
- E2E p95が許容範囲（目標: < 0.1秒）
- 復習品質指標（正答率/参照率）が伸びる or 安定

**停止ライン**:
- p95が急増（例えば2倍以上）
- 正答率が落ちる（復習が汚染として働いてる）

---

### Phase 4: Review effect ON（最後）

**目的**: 復習効果が正常に動作することを確認

**設定**:
```bash
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=full
export FWPKM_WRITE_ENABLED=1
export FWPKM_REVIEW_EFFECT=1
```

**確認事項**:
- [ ] 復習効果が正常に動作
- [ ] メモリが太りすぎない
- [ ] 品質指標が改善している

**観測指標**:
- 復習品質指標（正答率/参照率）が改善
- メモリ使用量が正常範囲内

**停止ライン**:
- 正答率が落ちる（復習が汚染として働いてる）
- メモリ使用量が異常に増える

---

## 🛑 停止ライン（止めどきルール）

### Read-onlyモード

- ❌ 矛盾検出率が急上昇（例：前日比2倍以上）
- ❌ ゲート遮断率が常時80%超え

### Write 10%

- ❌ 書き込み回数/分が想定の2倍以上に増える
- ❌ quarantineがactiveを上回る

### Write 100%

- ❌ p95が急増（例えば2倍以上）
- ❌ 正答率が落ちる

### Review effect ON

- ❌ 正答率が落ちる
- ❌ メモリ使用量が異常に増える

---

## 🔒 Kill Switchの使い方

### 即座に停止

```bash
# 環境変数を変更して再起動
export FWPKM_WRITE_ENABLED=0
# または
export FWPKM_ENABLED=0
```

### systemdの場合

```bash
# サービスファイルを編集
sudo systemctl edit mrl-memory.service

# 環境変数を設定
[Service]
Environment="FWPKM_WRITE_ENABLED=0"

# 再起動
sudo systemctl restart mrl-memory.service
```

### pm2の場合

```bash
# 環境変数を設定して再起動
pm2 restart mrl-memory --update-env --env production
```

---

## 🔄 障害時の切り戻し

### 1. 即座に停止

```bash
export FWPKM_WRITE_ENABLED=0
# サービス再起動
```

### 2. 前のフェーズに戻す

```bash
# Phase 2に戻す場合
export FWPKM_WRITE_MODE=sampled
export FWPKM_WRITE_SAMPLE_RATE=0.1
# サービス再起動
```

### 3. ログ確認

```bash
# エラーログを確認
tail -f /var/log/mrl-memory/error.log

# メトリクスを確認
python -c "from mrl_memory_metrics import MRLMemoryMetrics; m = MRLMemoryMetrics(); print(m.get_latency_stats())"
```

---

## 📊 観測指標の確認方法

### 1. メトリクスAPI（実装予定）

```bash
curl http://localhost:5105/api/metrics
```

### 2. ログから確認

```bash
# p95レイテンシ
grep "p95" /var/log/mrl-memory/metrics.log

# 書き込み回数/分
grep "write_count" /var/log/mrl-memory/metrics.log

# 矛盾検出率
grep "conflict_rate" /var/log/mrl-memory/metrics.log
```

### 3. Pythonスクリプトから確認

```python
from mrl_memory_metrics import MRLMemoryMetrics

metrics = MRLMemoryMetrics()

# レイテンシ統計
print(metrics.get_latency_stats())

# 書き込み回数統計
print(metrics.get_write_count_stats())

# ゲート遮断率統計
print(metrics.get_gate_block_rate_stats())

# 矛盾検出率統計
print(metrics.get_conflict_detection_rate_stats())
```

---

## 📝 チェックリスト

### 起動前

- [ ] `.env`ファイルが設定されている
- [ ] `REQUIRE_AUTH=1`が設定されている
- [ ] `API_KEY`が強力なキーに設定されている
- [ ] `RATE_LIMIT_PER_MIN`が適切に設定されている
- [ ] `MAX_INPUT_CHARS`が適切に設定されている

### 起動時

- [ ] 起動ログに`SECURITY: auth=enabled, ...`が表示される
- [ ] ヘルスチェックが正常（`curl http://localhost:5105/health`）

### ロールアウト中

- [ ] 観測指標を定期的に確認
- [ ] 停止ラインに達していないか確認
- [ ] ログに異常がないか確認

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: 本番運用準備完了
