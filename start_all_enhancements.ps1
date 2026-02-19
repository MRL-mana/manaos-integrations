# 全強化システム統合起動スクリプト
# Phase 1-3の全ツール・システムを起動

# Auto-admin check (optional - will continue if admin elevation fails)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== ManaOS統合システム 全強化ツール起動 ===" -ForegroundColor Cyan
Write-Host ""

# ディレクトリ移動
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Python環境確認
Write-Host "[1/4] Python環境を確認中..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Pythonが見つかりません" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# 依存パッケージ確認
Write-Host "[2/4] 依存パッケージを確認中..." -ForegroundColor Yellow
$requiredPackages = @("psutil", "requests", "watchdog", "schedule", "httpx")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "[WARNING] 不足しているパッケージ: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "インストールしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        pip install $missingPackages
    }
} else {
    Write-Host "[OK] 必要なパッケージがインストールされています" -ForegroundColor Green
}

# 起動オプション選択
Write-Host ""
Write-Host "[3/4] 起動するシステムを選択してください:" -ForegroundColor Yellow
Write-Host "1. Device Health Monitor (監視システム)"
Write-Host "2. Google Drive Sync Agent (ファイル同期)"
Write-Host "3. Unified Backup Manager (バックアップ管理)"
Write-Host "4. Device Orchestrator (デバイス統合管理)"
Write-Host "5. Cross-Platform File Sync (デバイス間同期)"
Write-Host "6. ADB Automation Toolkit (Pixel 7自動化)"
Write-Host "7. AI予測メンテナンスシステム"
Write-Host "8. すべて起動"
Write-Host "0. 終了"
Write-Host ""
Write-Host "選択 (0-8): " -NoNewline -ForegroundColor Yellow
$choice = Read-Host

# 選択に応じて起動
switch ($choice) {
    "1" {
        Write-Host "[4/4] Device Health Monitorを起動中..." -ForegroundColor Yellow
        python device_monitor_with_notifications.py
    }
    "2" {
        Write-Host "[4/4] Google Drive Sync Agentを起動中..." -ForegroundColor Yellow
        python google_drive_sync_agent.py
    }
    "3" {
        Write-Host "[4/4] Unified Backup Managerを起動中..." -ForegroundColor Yellow
        python unified_backup_manager.py
    }
    "4" {
        Write-Host "[4/4] Device Orchestratorを起動中..." -ForegroundColor Yellow
        python device_orchestrator.py
    }
    "5" {
        Write-Host "[4/4] Cross-Platform File Syncを起動中..." -ForegroundColor Yellow
        python cross_platform_file_sync.py
    }
    "6" {
        Write-Host "[4/4] ADB Automation Toolkitを起動中..." -ForegroundColor Yellow
        python adb_automation_toolkit.py
    }
    "7" {
        Write-Host "[4/4] AI予測メンテナンスシステムを起動中..." -ForegroundColor Yellow
        python ai_predictive_maintenance.py
    }
    "8" {
        Write-Host "[4/4] すべてのシステムを起動中..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "注意: 複数のシステムを同時に起動します" -ForegroundColor Yellow
        Write-Host "各システムは別のPowerShellウィンドウで起動されます" -ForegroundColor Yellow
        Write-Host ""
        
        # バックグラウンドで起動
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python device_monitor_with_notifications.py"
        Start-Sleep -Seconds 2
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python google_drive_sync_agent.py"
        Start-Sleep -Seconds 2
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python unified_backup_manager.py"
        
        Write-Host "主要システムを起動しました" -ForegroundColor Green
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
Write-Host "システムが起動しました" -ForegroundColor Green

