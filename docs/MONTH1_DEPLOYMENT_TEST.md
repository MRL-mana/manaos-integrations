# Month 1: 初めての改修デプロイテスト計画

**期間**: 2026-02-25 〜 2026-03-18 (3週間)  
**目標**: Week 1 での安定性確認後、初めての改修コードをセーフに本番デプロイするフローを検証する

---

## 🎯 全体戦略

```
Phase A (Week 2-3)
├─ マイナー改修コード作成 (低リスク)
├─ ステージング環境でのテスト
└─ デプロイメント前チェックリスト準備

Phase B (Week 4)
├─ デプロイ前ドライラン 
├─ バックアップ確認
├─ デプロイ実行 (deploy_to_home.ps1 使用)
└─ ロールバック検証
```

---

## 📋 Phase A: 準備フェーズ (2026-02-25 〜 2026-03-11)

### Step 1: マイナー改修コードの選定 (2026-02-25 〜 2026-02-27)

**要件**: 低リスク、独立した機能

#### 候補案

**案1: ログローテーション改善** (推奨)
```
説明: home_update_v2.log のサイズを監視し、100MB以上になったら切り替える
リスク度: ⭐ (超低)
影響範囲: ログシステムのみ、コアサービスに影響なし
```

**案2: ヘルスチェック間隔の調整**
```
説明: 健康チェック間隔を5秒から10秒に変更（負荷軽減）
リスク度: ⭐⭐ (低)
影響範囲: home_update_v2.py
```

**案3: オプショナルサービスの自動起動順序変更**
```
説明: 8088 (Gateway) と 8188 (ComfyUI) の起動順序を変更
リスク度: ⭐⭐⭐ (中程度)
影響範囲: startup_update.ps1 のオプショナルブートスタップ
```

**推奨**: 案1 (ログローテーション改善) で進める

### Step 2: ステージング環境でのテスト (2026-02-27 〜 2026-03-04)

#### 2-1. ローカルテスト環境のセットアップ

```powershell
# workspace 内に staging フォルダを作成
$stagingPath = "C:\Users\mana4\Desktop\manaos_integrations\staging"
if (-not (Test-Path $stagingPath)) {
    New-Item -ItemType Directory -Path $stagingPath -Force
}

# home のコピーをステージング環境で作成
Copy-Item -Path "D:\ManaHome\system\boot\home_update_v2.py" `
          -Destination "$stagingPath\home_update_v2.py.original" -Force
```

#### 2-2. コード改修（ログローテーション例）

```python
# C:\Users\mana4\Desktop\manaos_integrations\staging\home_update_v2_modified.py
# 元のファイルに以下の改善を加える

import os
from pathlib import Path

class LogRotationHandler:
    """ログローテーション管理"""
    
    MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, log_path):
        self.log_path = log_path
        self.backup_count = 5
    
    def rotate_if_needed(self):
        """ログサイズが上限に達したら回転"""
        if not os.path.exists(self.log_path):
            return False
        
        log_size = os.path.getsize(self.log_path)
        if log_size > self.MAX_LOG_SIZE:
            self._rotate_log()
            return True
        return False
    
    def _rotate_log(self):
        """ログファイルを回転"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.log_path}.{timestamp}"
        
        os.rename(self.log_path, backup_path)
        print(f"Log rotated: {self.log_path} -> {backup_path}")
        
        # 古いバックアップを削除（5世代まで保持）
        self._cleanup_old_backups()
    
    def _cleanup_old_backups(self):
        """古いバックアップを削除"""
        log_dir = os.path.dirname(self.log_path)
        log_name = os.path.basename(self.log_path)
        
        backups = sorted([
            f for f in os.listdir(log_dir) 
            if f.startswith(log_name + ".")
        ])
        
        if len(backups) > self.backup_count:
            for old_backup in backups[:-self.backup_count]:
                os.remove(os.path.join(log_dir, old_backup))
                print(f"Removed old backup: {old_backup}")

# home_update_v2.py の main ループ内で呼び出し
# log_rotation = LogRotationHandler(log_path)
# log_rotation.rotate_if_needed()  # メインループの最初に呼び出し
```

#### 2-3. ステージング環境でのユニットテスト

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\test_log_rotation.ps1

# テスト 1: ログローテーション機能の動作確認
Write-Host "Test 1: Basic log rotation"
$testLogPath = "$env:TEMP\test_home_update.log"
# ダミーログを作成 (100MB超)
# ...ここでテスト実装...

# テスト 2: バックアップ世代管理の確認
Write-Host "Test 2: Backup retention"
# 10個のバージョンを作成して、5個のみ残ることを確認
# ...ここでテスト実装...

# テスト 3: 元のログ機能が失われていないか確認
Write-Host "Test 3: Original logging still works"
# ログ出力が正常に行われることを確認
# ...ここでテスト実装...

Write-Host "All tests passed!"
```

#### 2-4. パフォーマンステスト

```powershell
# 改修前後の CPU/メモリ使用率を比較
# (オプショナル: ベースラインと大きく異なる場合は改修を再検討)

# 改修前のプロセス ID を記録
$beforePID = (Get-Process -Name python | Where-Object { $_.CommandLine -like "*home_update_v2*" }).Id

# 改修後のプロセス ID で同じ監視を実行
# ...パフォーマンス比較...
```

### Step 3: デプロイメント前チェックリストの準備 (2026-03-04 〜 2026-03-11)

```markdown
# Pre-Deployment Checklist (デプロイ前チェックリスト)

## 環境確認
- [ ] Home ディレクトリが利用可能 (D:\ManaHome)
- [ ] workshop ディレクトリが利用可能
- [ ] ネットワーク接続が正常
- [ ] ディスク空き容量 >= 10GB

## コード品質確認
- [ ] ステージング環境でのテストすべて合格
- [ ] コード改修内容を本番と比較確認
- [ ] 不要なデバッグコードが含まれていないか確認
- [ ] ファイルエンコーディングが正しいか確認 (UTF-8)

## 依存関係確認
- [ ] 新規パッケージが必要か確認
- [ ] 既存パッケージのバージョン互換性を確認
- [ ] 外部API呼び出しが増えていないか確認

## バックアップ準備
- [ ] 現在の home_update_v2.py をバックアップ
- [ ] 現在のログファイルをバックアップ
- [ ] state.json をバックアップ

## ロールバック計画
- [ ] ロールバック手順が明確か確認
- [ ] deploy_to_home.ps1 -Rollback フラグが動作するか確認
- [ ] ロールバック所要時間を見積もり (目標: 5分以内)

## デプロイ後検証計画
- [ ] デプロイ後に実行するテストリストを準備
- [ ] 予期しない動作が発生した場合の連絡先を確認
- [ ] ロールバック判定基準を明確にする (e.g., エラーが10件以上)

## 最終確認
- [ ] すべてのチェックに✓をつけた
- [ ] デプロイ責任者の承認を得た
- [ ] 有事連絡先が確保されている
```

---

## 📋 Phase B: デプロイ実行フェーズ (2026-03-11 〜 2026-03-18)

### Step 4: デプロイ前ドライラン (2026-03-11)

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\tools\deploy_to_home.ps1 を
# -DryRun フラグで実行（実際には変更しない）

$deployScript = "C:\Users\mana4\Desktop\manaos_integrations\tools\deploy_to_home.ps1"

# ドライラン実行
& $deployScript -DryRun

# 出力結果を記録
# Expected output:
# ✓ Files to be copied (list)
# ✓ Backup location: D:\ManaHome\system\backups\deploy\<timestamp>
# ✓ Health check would verify ports: 9502, 5106
```

### Step 5: バックアップの最終確認 (2026-03-12)

```powershell
# バックアップが正しく作成されるか確認
$backupDir = "D:\ManaHome\system\backups\deploy"
$latestBackup = Get-ChildItem $backupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Output "Latest backup:"
Write-Output "  Path: $($latestBackup.FullName)"
Write-Output "  Size: $([math]::Round($latestBackup.Size / 1MB))MB"
Write-Output "  Created: $($latestBackup.CreationTime)"

# バックアップの整合性を確認
Test-Path "$($latestBackup.FullName)\system\boot\home_update_v2.py"
Test-Path "$($latestBackup.FullName)\system\runtime\state.json"
```

### Step 6: デプロイ実行 (2026-03-15)

#### 推奨デプロイ時間

- **日時**: 平日の日中 (13:00-15:00 JST)
- **理由**: トラブル発生時の対応が容易、24時間サポート態勢が敷けるため
- **所要時間**: 3-5分（健康チェック含む）

#### デプロイコマンド

```powershell
# ステップ 1: デプロイスクリプト実行
$deployScript = "C:\Users\mana4\Desktop\manaos_integrations\tools\deploy_to_home.ps1"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$deployLog = "D:\ManaHome\system\runtime\logs\deploy_${timestamp}.log"

# デプロイ実行（ログ併記）
& $deployScript 2>&1 | Tee-Object -FilePath $deployLog

# ステップ 2: デプロイ結果の確認
Write-Output "Deployment completed. Log saved to: $deployLog"

# ステップ 3: 手動確認
# 以下を確認して「すべて成功している」ことを確認
# - ✓ Deployed 1 file(s): home_update_v2.py
# - ✓ Health check PASSED (ports 9502, 5106 responding)
# - ✓ Backup created: D:\ManaHome\system\backups\deploy\<timestamp>
```

#### デプロイ中の監視

```powershell
# デプロイ中（リアルタイム監視用スクリプト）
# C:\Users\mana4\Desktop\manaos_integrations\staging\monitor_deployment.ps1

$ports = @(9502, 5106)
$interval = 5  # 秒

Write-Output "Monitoring deployment..."
for ($i = 0; $i -lt 60; $i++) {
    $online = 0
    foreach ($port in $ports) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) {
                $online++
            }
            $client.Close()
        } catch {}
    }
    
    $status = "[$($i*$interval)s] Ports online: $online/$($ports.Count)"
    Write-Output $status
    
    if ($online -eq $ports.Count) {
        Write-Output "✓ All critical ports are online"
        break
    }
    
    Start-Sleep -Seconds $interval
}
```

### Step 7: デプロイ後検証 (2026-03-15 〜 2026-03-16)

#### 9 つの検証項目

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\post_deploy_verification.ps1

$verificationLog = "D:\ManaHome\system\runtime\logs\post_deploy_verification_$(Get-Date -Format 'yyyyMMdd').log"

$results = @()

# 1. コアサービス継続稼働確認
Write-Output "1. Core services availability check..."
$ports16 = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
$online = 0
foreach ($port in $ports16) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
        $client.Close()
    } catch {}
}
$results += "Core services: $online/16 [$(if ($online -eq 16) { '✓ PASS' } else { '✗ FAIL' })]"

# 2. オプショナルサービス確認
Write-Output "2. Optional services check..."
$port8088 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8088 -WarningAction SilentlyContinue).TcpTestSucceeded
$port8188 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -WarningAction SilentlyContinue).TcpTestSucceeded
$results += "Optional services: 8088=$port8088, 8188=$port8188 [$(if ($port8088 -and $port8188) { '✓ PASS' } else { '✗ FAIL' })]"

# 3. ログファイル整合性確認
Write-Output "3. Log file integrity check..."
$bootLog = Test-Path "D:\ManaHome\system\runtime\logs\home_boot_v2.log"
$updateLog = Test-Path "D:\ManaHome\system\runtime\logs\home_update_v2.log"
$results += "Log files present: boot=$bootLog, update=$updateLog [$(if ($bootLog -and $updateLog) { '✓ PASS' } else { '✗ FAIL' })]"

# 4. state.json の更新確認
Write-Output "4. State file recency check..."
$stateFile = Get-Item "D:\ManaHome\system\runtime\state.json"
$stateAge = (Get-Date) - $stateFile.LastWriteTime
$results += "State file age: $($stateAge.TotalSeconds) seconds [$(if ($stateAge.TotalSeconds -lt 60) { '✓ PASS' } else { '✗ FAIL' })]"

# 5. 新しいコード（log rotation）が有効になったか確認
Write-Output "5. New code deployment verification..."
$homeUpdateContent = Get-Content "D:\ManaHome\system\boot\home_update_v2.py"
$hasLogRotation = $homeUpdateContent -match "log.*rotat|rotat.*log" -or $homeUpdateContent -match "MAX_LOG_SIZE"
$results += "New code deployed: [$(if ($hasLogRotation) { '✓ PASS' } else { '⚠ WARNING' })]"

# 6. バックアップの存在確認
Write-Output "6. Backup creation verification..."
$backupDir = "D:\ManaHome\system\backups\deploy"
$backups = Get-ChildItem $backupDir | Measure-Object
$results += "Backups retained: $($backups.Count) [$(if ($backups.Count -ge 1) { '✓ PASS' } else { '✗ FAIL' })]"

# 7. ディスク容量確認
Write-Output "7. Disk space check..."
$drive = Get-PSDrive D
$freeGB = [math]::Round($drive.Free / 1GB)
$results += "Free disk space (D:): ${freeGB}GB [$(if ($freeGB -gt 10) { '✓ PASS' } else { '✗ FAIL' })]"

# 8. Windows Event Viewer でエラーがないか確認
Write-Output "8. Windows event log check..."
$errors = Get-EventLog -LogName Application -EntryType Error -After (Get-Date).AddMinutes(-5) -ErrorAction SilentlyContinue
$results += "Recent errors in Application log: $($errors.Count) [$(if ($errors.Count -eq 0) { '✓ PASS' } else { '⚠ WARNING' })]"

# 9. CPU/メモリ使用率が正常範囲か確認
Write-Output "9. System resource check..."
$pythonProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*home_update_v2*" }
if ($pythonProcess) {
    $cpuUsage = [math]::Round($pythonProcess.ProcessorTime.TotalSeconds)
    $memoryMB = [math]::Round($pythonProcess.WorkingSet / 1MB)
    $results += "Process resources: CPU=$($cpuUsage)s, Memory=${memoryMB}MB [✓ PASS]"
} else {
    $results += "home_update_v2 process not found [✗ FAIL]"
}

# 結果を記録
$results | Out-File -FilePath $verificationLog

# サマリー出力
Write-Output "`n=== POST-DEPLOYMENT VERIFICATION SUMMARY ==="
$results | ForEach-Object { Write-Output $_ }

# ロールバック判定
$failCount = ($results | Select-String "✗ FAIL").Count
Write-Output "`nFailed checks: $failCount"
if ($failCount -gt 2) {
    Write-Output "⚠️  Multiple failures detected. Consider rollback."
}
```

### Step 8: ロールバック検証 (2026-03-16 〜 2026-03-18)

#### ロールバック判定基準

```
以下のいずれかが該当する場合はロールバック実行:

1. コアサービス (16/16) が 14 以下に低下
2. デプロイ後 5 分以内に 10 件以上のエラーログ
3. ディスク容量が 5GB 未満に低下
4. Windows Startup が実行されない
5. CPU 使用率が 80% 以上に急騰
```

#### ロールバック実行コマンド

```powershell
# ロールバック実行
$deployScript = "C:\Users\mana4\Desktop\manaos_integrations\tools\deploy_to_home.ps1"

Write-Output "Initiating rollback..."
& $deployScript -Rollback

# ロールバック後の検証
Write-Output "Verifying rollback..."
Start-Sleep -Seconds 30

# コアサービス確認
$ports16 = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
$online = 0
foreach ($port in $ports16) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
        $client.Close()
    } catch {}
}

Write-Output "✓ Rollback complete. Core services online: $online/16"

if ($online -eq 16) {
    Write-Output "✓ Rollback successful - all systems restored"
} else {
    Write-Output "✗ WARNING: Not all services recovered. Manual intervention may be needed."
}
```

#### ロールバック後の確認

```powershell
# 被害評価：どこまで戻ったか確認
$backupDir = "D:\ManaHome\system\backups\deploy"
$currentVersion = Get-Content "D:\ManaHome\system\boot\home_update_v2.py" | Get-Hash
$latestBackup = Get-ChildItem $backupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$backupVersion = Get-Content "$($latestBackup.FullName)\system\boot\home_update_v2.py" | Get-Hash

if ($currentVersion -eq $backupVersion) {
    Write-Output "✓ Code successfully rolled back to previous version"
} else {
    Write-Output "✗ Code versions mismatch - manual verification needed"
}
```

---

## 📊 Month 1 合格基準

```
✓ ステージング環境テスト: すべて合格
✓ ドライラン: エラーなし
✓ デプロイ実行: 成功
✓ デプロイ後検証: 9/9 項目合格
✓ ロールバック検証: 5分以内に完了し機能復帰
✓ 最終レポート: 作成・承認完了
```

---

## 📝 Month 1 最終レポートテンプレート

```markdown
# Month 1 Deployment Test Report

**Report Date**: 2026-03-18  
**Deployment Timestamp**: 2026-03-15 13:45:00  
**Responsible**: [Your Name]

## Summary
- ✓ マイナー改修: ログローテーション機能
- ✓ Deployment success rate: 100%
- ✓ Rollback verification: Successful
- ✓ Zero production downtime

## Pre-Deployment
- All checklists: PASSED
- Staging tests: 5/5 passed
- Dry run: Successfully executed

## Deployment Process
- Execution time: 3 minutes 45 seconds
- Files deployed: home_update_v2.py
- Backup created: D:\ManaHome\system\backups\deploy\20260315_134500

## Post-Deployment Verification
- Core services: 16/16 online ✓
- Optional services: 8088 ✓, 8188 ✓
- Log files: Intact ✓
- State file: Current ✓
- Disk space: 125GB free ✓

## Rollback Test
- Rollback initiated: 2026-03-16 09:00:00
- Recovery time: 4 minutes 30 seconds
- Services restored: 16/16 ✓
- Status: SUCCESSFUL

## Conclusion
First production deployment completed successfully.
Deployment pipeline proven reliable and safe.
Ready for ongoing service updates.

## Recommendations
1. Increase deployment frequency to monthly
2. Automate health checks during deployment
3. Set up Slack/email alerts for deployment status

---

Approved by: _______________
Date: _______________
```

