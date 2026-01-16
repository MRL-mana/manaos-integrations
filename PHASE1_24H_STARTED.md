# Phase 1 24時間運用 - 開始記録

## ✅ 運用開始

**開始日時**: 2026-01-15 12:32

---

## 📊 初期状態

### 最初のスナップショット（12:32）

- **ファイル**: `snapshots/2026-01-15/12.json`
- **e2e_p95_sec**: 0.000640秒
- **writes_per_min**: 0（Read-onlyで正常）
- **storage_delta**: 0（Read-onlyで正常）
- **http_5xx_last_60min**: 0
- **gate_block_rate**: 0
- **contradiction_rate**: 0

---

## 🔄 自動化設定

### Windows Task Scheduler

**タスク名**: `MRL_Memory_Phase1_Hourly_Snapshot`

**設定方法**:
```powershell
# 自動設定スクリプトを実行
.\setup_phase1_hourly_snapshot.ps1
```

**実行間隔**: 毎時0分

**保存先**: `snapshots/YYYY-MM-DD/HH.json`

---

## 📋 運用チェックリスト

### 毎時（自動）

- [x] 12:32 - 最初のスナップショット取得完了
- [ ] 13:00 - スナップショット取得（自動）
- [ ] 14:00 - スナップショット取得（自動）
- [ ] ...（24時間継続）

### 24時間後

- [ ] `phase1_24h_summary.py` で集計
- [ ] `phase2_stop_checker.py --go` でGo判定
- [ ] Goなら Phase 2（Write 10%）に昇格

---

## ⚠️ 注意事項

### 変更時の対応

- **env変更・再起動・設定調整**が発生したら:
  1. その時刻のsnapshotファイル名に `_CHANGE` を付ける
  2. 変更直後に1回だけ warmup を取る（軽くでOK）
  3. その後は通常運用に戻す

**例**:
- 通常: `snapshots/2026-01-15/13.json`
- 変更時: `snapshots/2026-01-15/13_CHANGE.json`

### スナップショット欠損時の対応

- **1回欠損**: 無視でOK（ルール通り）
- **連続2回欠損**: **「観測系の復旧」だけ**やって戻す（機能追加とかはしない）

---

## 📊 24h終了後の共有

24時間運用終了後、以下を共有してください：

```bash
# 集計実行
python phase1_24h_summary.py snapshots/2026-01-15 phase1_metrics_snapshot_baseline.json 24

# 出力をそのまま貼り付け
```

---

**作成日時**: 2026-01-15 12:32  
**ステータス**: Phase 1 24時間運用開始
