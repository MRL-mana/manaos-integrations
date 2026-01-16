# Phase 1 → Phase 2 ロードマップ（実測値ベース・最終確定版）

## ✅ Phase 1 完了（確定）

### 実測値（baseline / warmup）

- **baseline p95**: 0.000263秒
- **warmup p95**: 0.000640秒（約2.4倍、負荷で自然な増加）
- **writes_per_min**: 0（Read-onlyで正常）
- **storage_delta**: 0（Read-onlyで正常）

**判定結果**: **GO（Phase 1継続）**

---

## 📋 Phase 2 進行条件（実測値ベース）

Phase 1を **24時間以上** 回して、以下を満たしたら Phase 2 へ：

### 必須条件

1. **Read-only健全性が継続**
   - `writes_per_min = 0` が維持
   - `storage_delta = 0` が維持

2. **安定性**
   - `http_5xx_last_60min = 0` を維持（少数出たら原因調査→収束確認）
   - `e2e_p95_sec >= 0.000789`（baseline × 3.0）が**3回連続**継続していない

3. **品質シグナル**
   - `contradiction_rate >= 0.05`（5%）が**3回連続**継続していない
   - `gate_block_rate >= 0.95`（95%）が**3回連続**継続していない

詳細: `PHASE2_GO_CONDITIONS_FINAL.md`

---

## 🚨 Phase 2 停止ライン（実測値ベース）

Writeが入ると、止めどきが変わる。以下が発生したら**即停止**：

1. **書き込み暴走**: Phase1比で**10倍以上**が継続
2. **ストレージ汚染**: `quarantine_entries` が `scratchpad_entries` を上回る
3. **矛盾検出率の暴走**: 0.10（10%）以上が継続
4. **レイテンシの暴走**: 0.001052秒（baseline × 4.0）以上が継続
5. **重大エラー**: `http_5xx_last_60min >= 3`

詳細: `PHASE2_STOP_CONDITIONS_FINAL.md`

---

## 📊 24時間運用の監視方法

### 1時間ごとのスナップショット

```bash
# 1時間ごとに実行（cron/systemd timerで自動化推奨）
python phase1_metrics_snapshot.py phase1_metrics_snapshot_hourly.json phase1_metrics_snapshot_baseline.json
```

### 停止判定（自動）

```bash
# 1時間ごとに実行
python phase2_stop_checker.py phase1_metrics_snapshot_hourly.json phase1_metrics_snapshot_baseline.json
```

### ダッシュボード確認

```bash
# 定期的に確認
python mrl_memory_dashboard.py
```

---

## 🔄 Phase 2への切り替え手順

Phase 2 Go条件を満たしたら：

### 1. `.env`を更新

```bash
# .envファイルを編集
FWPKM_WRITE_MODE=sampled
FWPKM_WRITE_SAMPLE_RATE=0.1
FWPKM_WRITE_ENABLED=1
FWPKM_REVIEW_EFFECT=0
```

### 2. サービス再起動

```bash
# systemdの場合
sudo systemctl restart mrl-memory

# PM2の場合
pm2 restart mrl-memory --update-env

# 直接起動の場合
# プロセスを停止して再起動
```

### 3. 起動確認

```bash
# ダッシュボードを確認
python mrl_memory_dashboard.py

# スナップショットを取得
python phase1_metrics_snapshot.py phase1_metrics_snapshot_phase2_start.json
```

---

## 🛑 停止手順

停止条件に該当したら：

### 1. Kill Switchを有効化

```bash
# .envファイルを編集
FWPKM_ENABLED=0
FWPKM_WRITE_ENABLED=0
```

### 2. サービス再起動

```bash
# systemdの場合
sudo systemctl restart mrl-memory

# PM2の場合
pm2 restart mrl-memory --update-env
```

### 3. ログを確認して原因を特定

```bash
# Windows
Get-Content mrl_memory.log | Select-String "ERROR"

# Linux
tail -f /var/log/mrl-memory/error.log | grep "ERROR"
```

---

## 📝 チェックリスト（24時間後）

- [ ] `writes_per_min = 0` が維持
- [ ] `storage_delta = 0` が維持
- [ ] `http_5xx_last_60min = 0`（または1〜2で原因調査済み）
- [ ] `e2e_p95_sec >= 0.000789`（baseline × 3.0）が**3回連続**継続していない
- [ ] `contradiction_rate >= 0.05`（5%）が**3回連続**継続していない
- [ ] `gate_block_rate >= 0.95`（95%）が**3回連続**継続していない

**すべてチェック → Phase 2へ**

---

## 📝 チェックリスト（Phase 2開始後、1時間ごと）

- [ ] `writes_per_min` が想定範囲内（Phase1比10倍未満）
- [ ] `quarantine_entries` が `scratchpad_entries` を上回っていない
- [ ] `contradiction_rate < 0.10`（10%）
- [ ] `e2e_p95_sec < 0.001052`（baseline × 4.0）
- [ ] `http_5xx_last_60min < 3`

**いずれか1つでも該当 → 即停止**

---

## ⚠️ 注意事項

### 単発スパイク vs 継続

- **単発スパイク**: 一時的な負荷増加によるもの（OK）
- **継続**: 1時間以上継続する異常値（NG）

判定方法: 1時間ごとのスナップショットで**3回連続**で閾値を超えたら「継続」と判定。

### `/api/metrics` のセキュリティ対策

観測が止まらないのは正義だけど、以下を守ると完璧：

- ✅ **認証必須**（既にOK）
- ✅ **レスポンスは軽量**（既にOK）
- ⚠️ **内部向けネットワーク限定**（できれば）
- ⚠️ 可能なら **`/api/metrics` は専用API_KEY（観測専用）** にする

---

**作成日**: 2026-01-15  
**バージョン**: 2.0（実測値ベース）  
**ステータス**: Phase 1完了、Phase 2準備完了
