# Phase 1 24時間運用 - 次のアクション

## ✅ 完了したこと

1. ✅ **最初のスナップショット取得完了**
   - ファイル: `snapshots/2026-01-15/12.json`
   - 時刻: 2026-01-15 12:32

2. ✅ **スナップショットディレクトリ作成完了**
   - ディレクトリ: `snapshots/2026-01-15/`

3. ✅ **自動化スクリプト作成完了**
   - バッチファイル: `phase1_snapshot_hourly.bat`
   - 設定スクリプト: `setup_phase1_hourly_snapshot.ps1`

---

## 🔄 次にやること（今すぐ）

### オプション1: 自動化を設定（推奨）

**Windows Task Schedulerで自動実行を設定**:

1. **管理者としてPowerShellを開く**
   - `Win + X` → 「Windows PowerShell (管理者)」

2. **以下のコマンドを実行**:
   ```powershell
   cd "C:\Users\mana4\Desktop\manaos_integrations"
   .\setup_phase1_hourly_snapshot.ps1
   ```

3. **または、GUIで設定**:
   - 詳細手順: `PHASE1_24H_MANUAL_SETUP.md` を参照

### オプション2: 手動実行（自動化できない場合）

**毎時0分に手動で実行**:

```powershell
$date = Get-Date -Format "yyyy-MM-dd"
$hour = Get-Date -Format "HH"
$snapshotPath = "snapshots\$date\$hour.json"
python phase1_metrics_snapshot.py $snapshotPath phase1_metrics_snapshot_baseline.json
```

**推奨**: スマートフォンのアラームを設定して、毎時0分に実行することを思い出す。

---

## 📊 24時間運用の進捗確認

### スナップショットの確認

```powershell
# 今日のスナップショット一覧
Get-ChildItem "snapshots\$(Get-Date -Format 'yyyy-MM-dd')" | Format-Table Name, LastWriteTime
```

### 集計（24時間後）

```powershell
$date = Get-Date -Format "yyyy-MM-dd"
python phase1_24h_summary.py "snapshots\$date" phase1_metrics_snapshot_baseline.json 24
```

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

## 📋 24時間後のチェックリスト

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

## 📝 24h終了後に共有してほしいもの

`phase1_24h_summary.py` の出力をそのまま貼ってください。

それを見て、以下を確定します：
- Phase 2 Go/No-Go（あなたのロジック通り）
- `writes_per_min_absolute=50` の最適化（request/min を織り込む）
- Phase 2の最初の"安全な観測期間"の提案（何時間見てから full に上げるか）

---

**作成日時**: 2026-01-15 12:32  
**ステータス**: Phase 1 24時間運用開始済み
