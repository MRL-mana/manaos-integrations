# オプションシステム起動スクリプト
# Device Orchestrator、Cross-Platform File Sync、ADB Automation Toolkit、AI予測メンテナンスシステムを起動

# Auto-admin check (optional - will continue if admin elevation fails)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== オプションシステム起動 ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "起動するオプションシステムを選択してください:" -ForegroundColor Yellow
Write-Host "1. Device Orchestrator (デバイス統合管理)"
Write-Host "2. Cross-Platform File Sync (デバイス間同期)"
Write-Host "3. ADB Automation Toolkit (Pixel 7自動化)"
Write-Host "4. AI予測メンテナンスシステム"
Write-Host "5. すべて起動"
Write-Host "6. Pixel 7 ADB ブリッジ (母艦 5122 / USB接続時)"
Write-Host "0. 終了"
Write-Host ""
Write-Host "選択 (0-6): " -NoNewline -ForegroundColor Yellow
$choice = Read-Host

switch ($choice) {
    "1" {
        Write-Host "Device Orchestratorを起動中..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python device_orchestrator.py"
        Write-Host "[OK] Device Orchestratorを起動しました" -ForegroundColor Green
    }
    "2" {
        Write-Host "Cross-Platform File Syncを起動中..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python cross_platform_file_sync.py"
        Write-Host "[OK] Cross-Platform File Syncを起動しました" -ForegroundColor Green
    }
    "3" {
        Write-Host "ADB Automation Toolkitを起動中..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python adb_automation_toolkit.py"
        Write-Host "[OK] ADB Automation Toolkitを起動しました" -ForegroundColor Green
    }
    "4" {
        Write-Host "AI予測メンテナンスシステムを起動中..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python ai_predictive_maintenance.py"
        Write-Host "[OK] AI予測メンテナンスシステムを起動しました" -ForegroundColor Green
    }
    "6" {
        Write-Host "Pixel 7 ADB ブリッジを起動中..." -ForegroundColor Cyan
        & "$scriptDir\start_pixel7_bridge.ps1"
        Write-Host "[OK] Pixel 7 ブリッジ (5122) を起動しました" -ForegroundColor Green
    }
    "5" {
        Write-Host "すべてのオプションシステムを起動中..." -ForegroundColor Cyan
        Write-Host ""
        # Pixel 7 ブリッジ（USB 接続時は先に起動）
        & "$scriptDir\start_pixel7_bridge.ps1"
        Start-Sleep -Seconds 1
        # Device Orchestrator
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python device_orchestrator.py"
        Start-Sleep -Seconds 2
        Write-Host "[OK] Device Orchestratorを起動しました" -ForegroundColor Green

        # Cross-Platform File Sync
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python cross_platform_file_sync.py"
        Start-Sleep -Seconds 2
        Write-Host "[OK] Cross-Platform File Syncを起動しました" -ForegroundColor Green

        # ADB Automation Toolkit
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python adb_automation_toolkit.py"
        Start-Sleep -Seconds 2
        Write-Host "[OK] ADB Automation Toolkitを起動しました" -ForegroundColor Green

        # AI予測メンテナンスシステム
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python ai_predictive_maintenance.py"
        Start-Sleep -Seconds 2
        Write-Host "[OK] AI予測メンテナンスシステムを起動しました" -ForegroundColor Green

        Write-Host ""
        Write-Host "=== 起動完了 ===" -ForegroundColor Green
        Write-Host "すべてのオプションシステムが起動しました" -ForegroundColor Green
        Write-Host ""
        Write-Host "起動したシステム:" -ForegroundColor Cyan
        Write-Host "  - Pixel 7 ADB ブリッジ (5122)" -ForegroundColor White
        Write-Host "  - Device Orchestrator" -ForegroundColor White
        Write-Host "  - Cross-Platform File Sync" -ForegroundColor White
        Write-Host "  - ADB Automation Toolkit" -ForegroundColor White
        Write-Host "  - AI予測メンテナンスシステム" -ForegroundColor White
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
Write-Host "オプションシステムが起動しました" -ForegroundColor Green
