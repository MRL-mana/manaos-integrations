# Phase 2 (Write 10%) 運用ルール（実測値ベース・最終確定版）

## 📋 Phase 2運用の全体像

Phase 1（Read-only）が24時間以上安定したら、**Write 10%（sampled 0.1）** に移行。

---

## 🎯 Phase 2 Go条件（実測値ベース）

### 実測値（Phase 1 baseline/warmup）

- **baseline p95**: 0.000263秒
- **warmup p95**: 0.000640秒（約2.4倍、負荷で自然な増加）
- **baseline writes_per_min**: 0（Read-only）

### 必須条件（すべて満たす必要がある）

#### 1. Read-only健全性が継続

- [ ] `writes_per_min = 0` が維持（24時間を通して）
- [ ] `storage_delta = 0` が維持（scratchpad/quarantine/promoted 全部0）
- [ ] `config.write_mode = readonly` が維持

#### 2. 安定性（実測値ベース）

- [ ] `http_5xx_last_60min = 0` を維持
  - 少数（1〜2）出たら原因調査→収束確認
  - 3以上なら即停止
- [ ] `e2e_p95_sec >= 0.000789`（baseline × 3.0）が**継続していない**
  - baseline基準: 0.000263秒
  - 継続NG閾値: 0.000789秒（baseline × 3.0）以上が**3回連続**（=3時間）継続
  - 単発スパイクはOK、継続はNG

#### 3. 品質シグナル

- [ ] `contradiction_rate >= 0.05`（5%）が**継続していない**
  - 前時間比2倍以上が継続しない
  - 現在値: 0（Read-onlyでは正常）
  - 注意閾値: 0.05（5%）以上が**3回連続**（=3時間）継続
- [ ] `gate_block_rate >= 0.95`（95%）が**継続していない**
  - 現在値: 0（Read-onlyでは正常）
  - 注意閾値: 0.80（80%）以上が継続
  - 停止閾値: 0.95（95%）以上が**3回連続**（=3時間）継続

---

## 🚨 Phase 2 Stop条件（即 Kill Switch）

### 即停止条件（いずれか1つでも該当したら即停止）

#### 1. 書き込み暴走

- **停止閾値**: Phase1比で**10倍以上**が継続
  - 例: Phase1で0、Phase2で10以上が継続
  - または: 想定値（例: 5/分）の**2倍以上**が継続

#### 2. ストレージ汚染

- **停止閾値**: `quarantine_entries` が `scratchpad_entries` を上回る
  - または: `quarantine_entries` が前時間比**2倍以上**が継続
  - 意味: 汚染 or 競合が優勢になっている

#### 3. 矛盾検出率の暴走

- **停止閾値**: 0.10（10%）以上が継続
  - または: 前時間比**2倍以上**が継続

#### 4. レイテンシの暴走

- **停止閾値**: Phase1比で+300%が継続
  - **baseline基準**: 0.000263秒
  - **停止閾値**: 0.001052秒（baseline × 4.0）以上が継続
  - 単発スパイクはOK、継続はNG

#### 5. 重大エラー

- **停止閾値**: `http_5xx_last_60min >= 3`
  - 3以上なら即停止（ロールアウトどころじゃない）

---

## 📊 監視方法（1時間ごと）

### スナップショット取得

```bash
# 1時間ごとのスナップショットを取得
python phase1_metrics_snapshot.py phase1_metrics_snapshot_hourly.json phase1_metrics_snapshot_baseline.json

# 停止判定（自動）
python phase2_stop_checker.py phase1_metrics_snapshot_hourly.json phase1_metrics_snapshot_baseline.json
```

### ダッシュボード確認

```bash
# ダッシュボードを表示
python mrl_memory_dashboard.py
```

---

## 🔄 Phase 2への切り替え手順

Phase 2 Go条件を満たしたら：

```bash
# .envを更新
# FWPKM_WRITE_MODE=sampled
# FWPKM_WRITE_SAMPLE_RATE=0.1
# FWPKM_WRITE_ENABLED=1

# Phase 2に切り替え（rollout_commands.shを使用）
./rollout_commands.sh phase2

# サービス再起動（systemdの場合）
sudo systemctl restart mrl-memory

# または（PM2の場合）
pm2 restart mrl-memory --update-env

# 起動確認
python mrl_memory_dashboard.py
```

---

## 🛑 停止手順

停止条件に該当したら：

```bash
# Kill Switchを有効化
export FWPKM_ENABLED=0
export FWPKM_WRITE_ENABLED=0

# サービス再起動（systemdの場合）
sudo systemctl restart mrl-memory

# または（PM2の場合）
pm2 restart mrl-memory --update-env

# ログを確認して原因を特定
# Windows: Get-Content mrl_memory.log | Select-String "ERROR"
# Linux: tail -f /var/log/mrl-memory/error.log | grep "ERROR"
```

---

## ⚠️ 注意事項

### 単発スパイク vs 継続

- **単発スパイク**: 一時的な負荷増加によるもの（OK）
- **継続**: 1時間以上継続する異常値（NG）

判定方法: 1時間ごとのスナップショットで**3回連続**で閾値を超えたら「継続」と判定。

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

**作成日**: 2026-01-15  
**バージョン**: 2.0（実測値ベース）  
**ステータス**: Phase 2運用ルール最終確定
