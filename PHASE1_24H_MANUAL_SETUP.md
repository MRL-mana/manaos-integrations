# Phase 1 24時間運用 - 手動設定ガイド（Windows Task Scheduler）

## 📋 現在の状態

**開始日時**: 2026-01-15 12:32

**最初のスナップショット**: ✅ 取得完了
- ファイル: `snapshots/2026-01-15/12.json`
- 状態: 正常

**自動化設定**: ⚠️ 管理者権限が必要な可能性があります

---

## 🔧 手動設定方法（管理者権限で実行）

### 方法1: PowerShell（管理者として実行）

```powershell
# 管理者としてPowerShellを開く
# 以下のコマンドを実行

$scriptDir = "C:\Users\mana4\Desktop\manaos_integrations"
$batchFile = Join-Path $scriptDir "phase1_snapshot_hourly.bat"
$taskName = "MRL_Memory_Phase1_Hourly_Snapshot"

$action = New-ScheduledTaskAction -Execute $batchFile -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Phase 1 24h運用: 毎時メトリクススナップショット取得"
```

### 方法2: Task Scheduler GUI（推奨）

1. **Task Schedulerを開く**
   - `Win + R` → `taskschd.msc` → Enter

2. **タスクの作成**
   - 右側の「タスクの作成」をクリック

3. **全般タブ**
   - 名前: `MRL_Memory_Phase1_Hourly_Snapshot`
   - 説明: `Phase 1 24h運用: 毎時メトリクススナップショット取得`
   - 「最上位の特権で実行する」にチェック

4. **トリガータブ**
   - 「新規」をクリック
   - タスクの開始: 「スケジュールに従う」
   - 開始: 今日の日付、次の時間（例: 13:00）
   - 繰り返し間隔: 1時間
   - 期間: 無期限

5. **操作タブ**
   - 「新規」をクリック
   - 操作: 「プログラムの開始」
   - プログラム/スクリプト: `C:\Users\mana4\Desktop\manaos_integrations\phase1_snapshot_hourly.bat`
   - 開始場所: `C:\Users\mana4\Desktop\manaos_integrations`

6. **条件タブ**
   - 「コンピューターがAC電源を使っている場合のみタスクを開始する」のチェックを外す
   - 「バッテリーで動作している場合、タスクを停止する」のチェックを外す

7. **設定タブ**
   - 「タスクをすぐに実行できる場合は、スケジュールされた時刻をスキップする」にチェック

8. **OK** をクリックして保存

---

## ✅ 設定確認

### タスクの状態確認

```powershell
Get-ScheduledTask -TaskName "MRL_Memory_Phase1_Hourly_Snapshot"
```

### タスクの実行履歴確認

```powershell
Get-ScheduledTaskInfo -TaskName "MRL_Memory_Phase1_Hourly_Snapshot"
```

### 手動実行（テスト）

```powershell
Start-ScheduledTask -TaskName "MRL_Memory_Phase1_Hourly_Snapshot"
```

---

## 🔄 代替方法: 手動実行（自動化できない場合）

自動化が難しい場合は、**手動で毎時実行**してください：

```powershell
# 毎時0分に実行
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
Get-ChildItem "snapshots\$(Get-Date -Format 'yyyy-MM-dd')" | Sort-Object Name
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

---

**作成日時**: 2026-01-15 12:32  
**ステータス**: Phase 1 24時間運用開始（手動設定ガイド）
