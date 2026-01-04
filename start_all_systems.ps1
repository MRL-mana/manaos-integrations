# 全システム統合起動スクリプト
# Phase 1-3の全ツール・システムを起動

# Auto-admin check (optional - will continue if admin elevation fails)
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== ManaOS統合システム 全システム起動 ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. 通知設定確認
Write-Host "[1/6] 通知設定確認中..." -ForegroundColor Yellow
$notificationConfig = Join-Path $scriptDir "notification_hub_enhanced_config.json"
if (Test-Path $notificationConfig) {
    $config = Get-Content $notificationConfig | ConvertFrom-Json
    if ($config.slack_webhook_url) {
        Write-Host "  [OK] Slack通知設定済み" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Slack通知未設定" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARNING] 通知設定ファイルが見つかりません" -ForegroundColor Yellow
}

# 2. Google Drive認証確認
Write-Host "[2/6] Google Drive認証確認中..." -ForegroundColor Yellow
$credentialsFile = Join-Path $scriptDir "credentials.json"
$tokenFile = Join-Path $scriptDir "token.json"

if (Test-Path $credentialsFile) {
    Write-Host "  [OK] credentials.jsonが見つかりました" -ForegroundColor Green
    if (Test-Path $tokenFile) {
        Write-Host "  [OK] token.jsonが見つかりました（認証済み）" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] token.jsonが見つかりません（初回認証が必要）" -ForegroundColor Cyan
        Write-Host "    → Google Drive機能を使用する場合のみ必要です" -ForegroundColor Gray
    }
} else {
    Write-Host "  [INFO] credentials.jsonが見つかりません" -ForegroundColor Cyan
    Write-Host "    → Google Drive機能を使用する場合のみ必要です" -ForegroundColor Gray
}

# 3. API Gateway確認
Write-Host "[3/6] デバイスAPI Gateway確認中..." -ForegroundColor Yellow
$devices = @(
    @{ Name = "X280"; Endpoint = "http://100.127.121.20:5120/health" }
    @{ Name = "Konoha Server"; Endpoint = "http://100.93.120.33:5106/health" }
    @{ Name = "Pixel 7"; Endpoint = "http://100.127.121.20:5122/health" }
)

$onlineDevices = 0
foreach ($device in $devices) {
    try {
        $response = Invoke-WebRequest -Uri $device.Endpoint -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($device.Name) オンライン" -ForegroundColor Green
            $onlineDevices++
        }
    } catch {
        Write-Host "  [INFO] $($device.Name) オフライン（監視は継続します）" -ForegroundColor Cyan
    }
}

Write-Host "  オンライン: $onlineDevices / $($devices.Count)" -ForegroundColor $(if ($onlineDevices -eq $devices.Count) { "Green" } else { "Yellow" })

# 4. 依存パッケージ確認
Write-Host "[4/6] 依存パッケージ確認中..." -ForegroundColor Yellow
$requiredPackages = @("psutil", "requests", "watchdog", "schedule", "httpx")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "  [WARNING] 不足しているパッケージ: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "  インストールしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        pip install $missingPackages
    }
} else {
    Write-Host "  [OK] 必要なパッケージがインストールされています" -ForegroundColor Green
}

# 5. 起動確認
Write-Host "[5/6] システム起動準備完了" -ForegroundColor Green
Write-Host ""
Write-Host "起動するシステムを選択してください:" -ForegroundColor Yellow
Write-Host "1. Device Health Monitor (監視システム)"
Write-Host "2. Google Drive Sync Agent (ファイル同期)"
Write-Host "3. Unified Backup Manager (バックアップ管理)"
Write-Host "4. Device Orchestrator (デバイス統合管理)"
Write-Host "5. Cross-Platform File Sync (デバイス間同期)"
Write-Host "6. ADB Automation Toolkit (Pixel 7自動化)"
Write-Host "7. AI予測メンテナンスシステム"
Write-Host "8. すべて起動（推奨）"
Write-Host "0. 終了"
Write-Host ""
Write-Host "選択 (0-8): " -NoNewline -ForegroundColor Yellow
$choice = Read-Host

# 6. システム起動
Write-Host "[6/6] システム起動中..." -ForegroundColor Yellow
Write-Host ""

switch ($choice) {
    "1" {
        Write-Host "Device Health Monitorを起動中..." -ForegroundColor Cyan
        python device_monitor_with_notifications.py
    }
    "2" {
        Write-Host "Google Drive Sync Agentを起動中..." -ForegroundColor Cyan
        python google_drive_sync_agent.py
    }
    "3" {
        Write-Host "Unified Backup Managerを起動中..." -ForegroundColor Cyan
        python unified_backup_manager.py
    }
    "4" {
        Write-Host "Device Orchestratorを起動中..." -ForegroundColor Cyan
        python device_orchestrator.py
    }
    "5" {
        Write-Host "Cross-Platform File Syncを起動中..." -ForegroundColor Cyan
        python cross_platform_file_sync.py
    }
    "6" {
        Write-Host "ADB Automation Toolkitを起動中..." -ForegroundColor Cyan
        python adb_automation_toolkit.py
    }
    "7" {
        Write-Host "AI予測メンテナンスシステムを起動中..." -ForegroundColor Cyan
        python ai_predictive_maintenance.py
    }
    "8" {
        Write-Host "すべてのシステムを起動中..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "注意: 複数のシステムを同時に起動します" -ForegroundColor Yellow
        Write-Host "各システムは別のPowerShellウィンドウで起動されます" -ForegroundColor Yellow
        Write-Host ""
        
        # 主要システムをバックグラウンドで起動
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python device_monitor_with_notifications.py"
        Start-Sleep -Seconds 2
        
        Write-Host "[OK] Device Health Monitorを起動しました" -ForegroundColor Green
        
        # Google Drive Sync Agent（認証済みの場合のみ）
        if (Test-Path $tokenFile) {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python google_drive_sync_agent.py"
            Start-Sleep -Seconds 2
            Write-Host "[OK] Google Drive Sync Agentを起動しました" -ForegroundColor Green
        } else {
            Write-Host "[SKIP] Google Drive Sync Agent（認証未完了）" -ForegroundColor Gray
        }
        
        # Unified Backup Manager
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python unified_backup_manager.py"
        Start-Sleep -Seconds 2
        Write-Host "[OK] Unified Backup Managerを起動しました" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "=== 起動完了 ===" -ForegroundColor Green
        Write-Host "主要システムが起動しました" -ForegroundColor Green
        Write-Host ""
        Write-Host "起動したシステム:" -ForegroundColor Cyan
        Write-Host "  - Device Health Monitor" -ForegroundColor White
        if (Test-Path $tokenFile) {
            Write-Host "  - Google Drive Sync Agent" -ForegroundColor White
        }
        Write-Host "  - Unified Backup Manager" -ForegroundColor White
        Write-Host ""
        Write-Host "各システムのログを確認するには、起動したPowerShellウィンドウを確認してください" -ForegroundColor Gray
    }
    "0" {
        Write-Host "終了します" -ForegroundColor Cyan
        exit 0
    }
    default {
        Write-Host "[ERROR] 無効な選択です" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "System started successfully" -ForegroundColor Green

