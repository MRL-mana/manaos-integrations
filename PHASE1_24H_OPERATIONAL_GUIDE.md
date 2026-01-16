# Phase 1 24時間運用ガイド（最小運用セット）

## 📊 24時間運用の最小セット

Phase 1を24時間運用するための最小限の運用セット（集計・チェック・自動停止のコツ）。

---

## 1. スナップショット取得（毎時）

### 自動化（推奨）

```bash
# cron/systemd timerで毎時実行（Linux）
0 * * * * cd /path/to/mrl_memory && python phase1_metrics_snapshot.py snapshots/hourly/phase1_metrics_snapshot_$(date +\%Y\%m\%d_\%H).json phase1_metrics_snapshot_baseline.json

# Task Schedulerで毎時実行（Windows）
# スケジュール: 毎時0分
# コマンド: python phase1_metrics_snapshot.py snapshots\hourly\phase1_metrics_snapshot_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%.json phase1_metrics_snapshot_baseline.json
```

### 手動実行

```bash
# 1時間ごとに実行
python phase1_metrics_snapshot.py snapshots/hourly/phase1_metrics_snapshot_20260115_08.json phase1_metrics_snapshot_baseline.json
```

---

## 2. 24時間集計（超ミニ）

### 集計スクリプト実行

```bash
# 24時間分のスナップショットを集計
python phase1_24h_summary.py snapshots/hourly phase1_metrics_snapshot_baseline.json 24
```

### 集計結果の確認項目

最低これだけ確認すればPhase 2判断が一瞬になる：

- **p95のmax / avg**: `e2e_p95_sec`の最大値と平均値
- **5xxの合計**: `http_5xx_last_60min`の合計
- **contradiction_rateのmax**: `contradiction_rate`の最大値
- **gate_block_rateのmax**: `gate_block_rate`の最大値
- **writes_per_min（当然0）確認**: Read-only健全性
- **storage_delta（当然0）確認**: Read-only健全性

---

## 3. Go条件チェック（自動）

### 継続判定チェック

```bash
# Phase 2 Go条件をチェック（継続判定対応）
python phase2_stop_checker.py --go snapshots/hourly phase1_metrics_snapshot_baseline.json 24
```

### 継続判定の仕組み

- **3回連続違反** = 3時間継続でNG判定
- 単発スパイクは許容、継続はNG

判定対象:
- `e2e_p95_sec >= 0.000789`（baseline × 3.0）が**3回連続**継続
- `contradiction_rate >= 0.05`（5%）が**3回連続**継続
- `gate_block_rate >= 0.95`（95%）が**3回連続**継続

---

## 4. 異常時の自動停止（すでに用意済み）

### Phase 1運用中にも使用可能

Phase 2に行く前でも、Phase 1の運用中に以下が起きうる：

- 5xxが出始める
- メトリクス取得失敗が続く

### 停止判定スクリプト実行

```bash
# 停止条件をチェック（単一スナップショット）
python phase2_stop_checker.py snapshots/hourly/phase1_metrics_snapshot_latest.json phase1_metrics_snapshot_baseline.json
```

---

## 5. メトリクス欠損の扱いルール（保険①）

24h運用では、以下のような欠損が起きることがある：

- snapshotが落ちる
- APIが一瞬落ちる
- `/api/metrics` がタイムアウトする

### 欠損の扱いルール

- ✅ **24hのうち snapshot欠損が1回まで** → その時刻は"無視"して継続判定
- ❌ **連続欠損が2回以上** → **判定不能（計測経路の問題）扱いで一旦停止**
  - Go/No-Go判定は行わず、観測復旧を優先

> 観測が死んだまま Phase 2 へ行くのが一番危険だからね。

`phase2_stop_checker.py --go` が自動的にこのルールを適用します。

---

## 5. Phase 1 24h運用中の"1行ルール"（地味に効く）

**何か変えたら必ず snapshot 取る**

- env変更
- 再起動
- 設定調整
- その他、システムに変更を加えた場合

### 変更時のスナップショット命名（運用がさらに気持ちよくなる）

再起動や.env変更が発生したら、その時刻のsnapshotファイル名に `_CHANGE` をつけると後で神。

**例**:
- 通常: `snapshots/2026-01-15/13.json`
- 変更時: `snapshots/2026-01-15/13_CHANGE.json`

（人間が見ても一発で分かる）

これだけで原因追跡が楽になる。

---

## 6. 運用フロー（24時間運用）

### 1時間ごと

```bash
# 1. スナップショット取得
python phase1_metrics_snapshot.py snapshots/hourly/phase1_metrics_snapshot_$(date +\%Y\%m\%d_\%H).json phase1_metrics_snapshot_baseline.json

# 2. 停止判定（オプション）
python phase2_stop_checker.py snapshots/hourly/phase1_metrics_snapshot_latest.json phase1_metrics_snapshot_baseline.json
```

### 24時間後

```bash
# 1. 集計
python phase1_24h_summary.py snapshots/hourly phase1_metrics_snapshot_baseline.json 24

# 2. Go条件チェック
python phase2_stop_checker.py --go snapshots/hourly phase1_metrics_snapshot_baseline.json 24

# 3. ダッシュボード確認
python mrl_memory_dashboard.py
```

---

## 📝 チェックリスト（24時間後）

- [ ] スナップショットが24個以上ある（1時間ごと）
- [ ] `writes_per_min = 0` が維持（max値が0）
- [ ] `storage_delta = 0` が維持（max値が0）
- [ ] `http_5xx_last_60min` の合計 < 3
- [ ] `e2e_p95_sec` の最大値 < 0.000789秒（baseline × 3.0）
- [ ] `contradiction_rate` の最大値 < 0.05（5%）
- [ ] `gate_block_rate` の最大値 < 0.95（95%）
- [ ] `e2e_p95_sec >= 0.000789` が**3回連続**継続していない
- [ ] `contradiction_rate >= 0.05` が**3回連続**継続していない
- [ ] `gate_block_rate >= 0.95` が**3回連続**継続していない

**すべてチェック → Phase 2へ**

---

## ⚠️ 注意事項

### 単発スパイク vs 継続

- **単発スパイク**: 一時的な負荷増加によるもの（OK）
- **継続**: 3時間以上継続する異常値（NG）

判定方法: 1時間ごとのスナップショットで**3回連続**で閾値を超えたら「継続」と判定。

### スナップショット保存先

- **推奨（日付ディレクトリ切り）**: `snapshots/YYYY-MM-DD/HH.json`
  - 例: `snapshots/2026-01-15/00.json`, `snapshots/2026-01-15/01.json`
  - これにより summary が秒で書けるし、障害解析も神速になる
- **代替（フラット）**: `snapshots/hourly/` ディレクトリに保存
  - ファイル名: `phase1_metrics_snapshot_YYYYMMDD_HH.json`
- ベースライン: `phase1_metrics_snapshot_baseline.json`（固定）

---

## 🛡️ 24h運用中の最小の事故防止

### ✅ もし snapshot が欠損したら

- **1回欠損**: 無視でOK（ルール通り）
- **連続2回欠損**: **「観測系の復旧」だけ**やって戻す（機能追加とかはしない）

### ✅ もし `_CHANGE` が発生したら

- **変更直後に 1回だけ warmup 取る**（軽くでOK）
  - 例: `python phase1_warmup.py` を実行
- **その後は通常運用に戻す**
  - 変更が影響したかだけ切り分けできる

これやると、後で「CHANGEが効いたのか偶然か」が分かる。

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1 24時間運用ガイド完成
