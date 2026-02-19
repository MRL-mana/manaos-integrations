# Week 1: 運用安定性確認ガイド

**期間**: 2026-02-18 〜 2026-02-25 (7日間)  
**目標**: ManaOS Home の基本的な安定性を確認し、24/7 運用の信頼性を検証する

---

## 📋 Day 1: ベースライン測定 (2026-02-18)

### 具体的なタスク

1. **初期状態の記録**
   ```powershell
   # スクリプト: baseline_measurement.ps1
   $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
   $registryPath = "D:\ManaHome\system\services\registry.yaml"
   $statePath = "D:\ManaHome\system\runtime\state.json"
   
   # サービス数のカウント
   [System.Collections.ArrayList]$alwaysOn = @()
   [System.Collections.ArrayList]$optional = @()
   
   # registry.yaml を解析
   $registry = Get-Content $registryPath
   foreach ($line in $registry) {
       if ($line -match 'always_on: true') { $alwaysOn.Add($line) }
       if ($line -match 'always_on: false') { $optional.Add($line) }
   }
   
   Write-Output "[$timestamp] BASELINE MEASUREMENT"
   Write-Output "Always-on services: $($alwaysOn.Count)"
   Write-Output "Optional services: $($optional.Count)"
   Write-Output "Total: $($alwaysOn.Count + $optional.Count)"
   
   # 現在のサービス状態
   $state = Get-Content $statePath | ConvertFrom-Json
   Write-Output "Currently online: $($state.services_online) / $($alwaysOn.Count)"
   ```

2. **ログサイズの初期確認**
   - `D:\ManaHome\system\runtime\logs\home_boot_v2.log` の行数
   - `D:\ManaHome\system\runtime\logs\home_update_v2.log` の行数
   - `D:\ManaHome\system\runtime\logs\startup_update_bootstrap.log` の行数

3. **健康状態スナップショット**
   ```powershell
   # 16個のコアサービスポート確認
   $ports16 = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
   $online = 0
   foreach ($port in $ports16) {
       try {
           $client = New-Object System.Net.Sockets.TcpClient
           if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) {
               $online++
           }
           $client.Close()
       } catch {}
   }
   Write-Output "Core services online: $online/16"
   
   # オプショナルサービス確認
   $port8088 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8088 -WarningAction SilentlyContinue).TcpTestSucceeded
   $port8188 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -WarningAction SilentlyContinue).TcpTestSucceeded
   Write-Output "Optional services online: 8088=$port8088, 8188=$port8188"
   ```

### チェックリスト

- [ ] 初期ログサイズを記録
- [ ] 初期サービス状態を記録 (16/16 確認)
- [ ] オプショナルポート状態を記録 (8088, 8188)
- [ ] 記録を `D:\ManaHome\system\runtime\logs\week1_baseline_<DATE>.txt` に保存

---

## 📋 Day 2-3: 連続稼働テスト (2026-02-19 〜 2026-02-20)

### 具体的なタスク

1. **24時間連続稼働確認**
   - サービスが継続的にオンラインであることを確認
   - 自動再起動メカニズムが不要であることを確認

2. **毎日2回の健康チェック実行**
   ```powershell
   # 朝 (08:00) と 夜 (20:00) に実行
   # スクリプト: daily_health_check.ps1
   
   $reportFile = "D:\ManaHome\system\runtime\logs\health_check_$(Get-Date -Format 'yyyy-MM-dd').log"
   $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
   
   # コアサービス確認
   $ports16 = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
   $online = 0
   $failedPorts = @()
   
   foreach ($port in $ports16) {
       try {
           $client = New-Object System.Net.Sockets.TcpClient
           if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) {
               $online++
           } else {
               $failedPorts += $port
           }
           $client.Close()
       } catch {
           $failedPorts += $port
       }
   }
   
   $status = "$timestamp | Core: $online/16"
   if ($failedPorts.Count -gt 0) {
       $status += " | Failed: $($failedPorts -join ',')"
   }
   
   # オプショナルサービス
   $port8088 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8088 -WarningAction SilentlyContinue).TcpTestSucceeded
   $port8188 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -WarningAction SilentlyContinue).TcpTestSucceeded
   $status += " | Optional: 8088=$port8088, 8188=$port8188"
   
   Add-Content -Path $reportFile -Value $status
   Write-Output $status
   ```

3. **ログファイル増長監視**
   ```powershell
   # 各ログファイルのサイズと行数をトラッキング
   $bootLog = Get-Item "D:\ManaHome\system\runtime\logs\home_boot_v2.log"
   $updateLog = Get-Item "D:\ManaHome\system\runtime\logs\home_update_v2.log"
   
   Write-Output "Boot log: $($bootLog.Length / 1024)KB"
   Write-Output "Update log: $($updateLog.Length / 1024)KB"
   ```

### チェックリスト

- [ ] Day 2 朝 (08:00) - ヘルスチェック実行、結果記録
- [ ] Day 2 夜 (20:00) - ヘルスチェック実行、結果記録
- [ ] Day 3 朝 (08:00) - ヘルスチェック実行、結果記録
- [ ] Day 3 夜 (20:00) - ヘルスチェック実行、結果記録
- [ ] ログサイズが異常に増加していないか確認

---

## 📋 Day 4-5: 自動再起動テスト (2026-02-21 〜 2026-02-22)

### 具体的なタスク

1. **意図的なサービス停止テスト** (本番への影響は最小限)
   
   **注意**: オプショナルサービスのみテストする  
   ```powershell
   # Port 8088 (Moltbot Gateway) を停止
   $process = Get-Process | Where-Object { $_.Name -like "*gateway*" }
   if ($process) {
       Stop-Process -Id $process.Id -Force
       Write-Output "Stopped port 8088 service at $(Get-Date -Format 'HH:mm:ss')"
       
       # 5分待機
       Start-Sleep -Seconds 300
       
       # 自動再起動されたか確認
       $port8088 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8088 -WarningAction SilentlyContinue).TcpTestSucceeded
       Write-Output "Port 8088 recovered: $port8088 at $(Get-Date -Format 'HH:mm:ss')"
   }
   ```

2. **コアサービスは安全にテストしない** (重要)
   - ポート 9502 (Unified API) は停止テスト対象外
   - ポート 5106 (Orchestrator) は停止テスト対象外
   - これらは自動再起動メカニズムをテストする必要がないほど受信

3. **再起動イベントの記録**
   ```powershell
   # home_update_v2.log を確認して auto-restart イベントを検索
   $updateLog = "D:\ManaHome\system\runtime\logs\home_update_v2.log"
   $content = Get-Content $updateLog
   $restartEvents = $content | Select-String "restarting|recovered|online"
   
   Write-Output "Auto-restart events detected:"
   $restartEvents | ForEach-Object { Write-Output "  $_" }
   ```

### チェックリスト

- [ ] Day 4: Port 8088 停止テスト実行
- [ ] Day 4: 5分以内に自動復旧を確認
- [ ] Day 4: home_update_v2.log に復旧イベントが記録されているか確認
- [ ] Day 5: Port 8188 (ComfyUI) が問題なく稼働しているか確認
- [ ] テスト結果を `week1_restart_test_results.txt` に記録

---

## 📋 Day 6-7: ログ分析と最終確認 (2026-02-23 〜 2026-02-25)

### 具体的なタスク

1. **エラーと警告のログ分析**
   ```powershell
   # home_boot_v2.log からエラーを抽出
   $bootLog = "D:\ManaHome\system\runtime\logs\home_boot_v2.log"
   $bootErrors = Get-Content $bootLog | Select-String -Pattern "ERROR|FAILED|Exception"
   
   # home_update_v2.log からエラーを抽出
   $updateLog = "D:\ManaHome\system\runtime\logs\home_update_v2.log"
   $updateErrors = Get-Content $updateLog | Select-String -Pattern "ERROR|FAILED|Exception"
   
   # startup_update_bootstrap.log からエラーを抽出
   $suLog = "D:\ManaHome\system\runtime\logs\startup_update_bootstrap.log"
   $suErrors = Get-Content $suLog | Select-String -Pattern "ERROR|FAILED|Exception"
   
   Write-Output "Boot log errors: $($bootErrors.Count)"
   Write-Output "Update log errors: $($updateErrors.Count)"
   Write-Output "Bootstrap log errors: $($suErrors.Count)"
   ```

2. **安定性指標の集約**
   ```powershell
   # 7日間のヘルスチェック結果を集約
   $healthLogs = Get-ChildItem "D:\ManaHome\system\runtime\logs\health_check_*.log"
   
   $totalChecks = 0
   $successChecks = 0
   
   foreach ($log in $healthLogs) {
       $content = Get-Content $log.FullName
       foreach ($line in $content) {
           $totalChecks++
           if ($line -match "Core: 16/16") {
               $successChecks++
           }
       }
   }
   
   $successRate = ($successChecks / $totalChecks) * 100
   Write-Output "Week 1 Service Availability: $successRate%"
   Write-Output "Target: >= 99.5%"
   ```

3. **Windows Startup 自動実行の確認**
   ```powershell
   # ManaOS_AutoStart.cmd が登録されているか確認
   $startupFolder = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
   $autoStartFile = Join-Path $startupFolder 'ManaOS_AutoStart.cmd'
   
   if (Test-Path $autoStartFile) {
       Write-Output "✓ Windows Startup registration: Active"
       Write-Output "Location: $autoStartFile"
   } else {
       Write-Output "✗ Windows Startup registration: MISSING"
   }
   ```

4. **Week 1 最終レポート作成**
   ```powershell
   # 最終レポートテンプレート
   $report = @"
   # Week 1 Operational Stability Report
   
   **Report Date**: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
   **Analysis Period**: 2026-02-18 ~ 2026-02-25
   
   ## Service Availability
   - Core Services (16/16): [SUCCESS/FAILURE]
   - Optional Services (8088, 8188): [STATUS]
   - Average Uptime: [X%]
   
   ## Error Analysis
   - Boot log errors: [COUNT]
   - Update log errors: [COUNT]
   - Bootstrap log errors: [COUNT]
   
   ## Auto-Restart Tests
   - Port 8088 recovery time: [X minutes]
   - Recovery success rate: [X%]
   
   ## Windows Startup Integration
   - Auto-start on login: [CONFIRMED/NOT CONFIRMED]
   - No admin interaction required: [YES/NO]
   
   ## Conclusion
   [安定性評価: STABLE / STABLE WITH WARNINGS / UNSTABLE]
   
   ## Recommended Actions
   1. [Action 1]
   2. [Action 2]
   "@
   
   Set-Content -Path "D:\ManaHome\WEEK1_REPORT.md" -Value $report
   ```

### チェックリスト

- [ ] Day 6: ログエラー分析を実行
- [ ] Day 6: 7日間のヘルスチェック結果を集約
- [ ] Day 6: 可用性を計算 (>=99.5% が目標)
- [ ] Day 7: Windows Startup 自動実行を確認
- [ ] Day 7: 最終レポートを作成・保存

---

## 🎯 Week 1 合格基準

以下すべてを満たしたら Week 1 は **合格** です：

```
✓ Core services availability: 99.5% 以上
✓ Optional services auto-recovery: 100% 成功
✓ ログエラー数: 10 件以下
✓ Windows Startup 自動実行: 正常に動作
✓ Admin interaction: 不要
```

---

## 📝 実行スケジュール例

```
02/18 (火) 18:00 - 初期状態記録
02/19 (水) 08:00 - 健康チェック 1回目
02/19 (水) 20:00 - 健康チェック 2回目
02/20 (木) 08:00 - 健康チェック 3回目
02/20 (木) 20:00 - 健康チェック 4回目
02/21 (金) 14:00 - 自動再起動テスト 1回目
02/22 (土) 14:00 - 自動再起動テスト 2回目
02/23 (日) 10:00 - ログ分析開始
02/25 (火) 17:00 - 最終レポート完成
```

---

## 📊 ダッシュボード (オプショナル自動化)

```powershell
# 毎日の自動健康チェックを Windows Task Scheduler に登録
$taskName = "ManaOS_Health_Check_Daily"
$scriptPath = "D:\ManaHome\system\scripts\daily_health_check.ps1"

# 朝 8:00 と 夜 20:00 に自動実行
# Register-ScheduledTask -TaskName $taskName -Trigger @(
#     (New-ScheduledTaskTrigger -Daily -At "08:00"),
#     (New-ScheduledTaskTrigger -Daily -At "20:00")
# ) -Action (New-ScheduledTaskAction -Execute "powershell" -Argument "-File $scriptPath")
```

---

## 📞 トラブルシューティング

| 症状 | 原因 | 対応 |
|------|------|------|
| コア16サービスが15以下 | サービス停止 | `D:\ManaHome\system\boot\home_update_v2.py --auto-restart` 実行 |
| ログファイルが肥大化 | 無限ループ | `home_update_v2.log` の最後50行を確認、不具合箇所を特定 |
| Windows Startup 不動作 | ファイル削除 | `ManaOS_AutoStart.cmd` を再作成し Startup フォルダに配置 |
| Port 8088/8188 が常にオフ | 起動失敗 | コア16サービスがオンラインか先に確認 |

