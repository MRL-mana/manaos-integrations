# Device Health Monitor起動スクリプト
# 通知機能付きデバイス監視システムを起動

# Auto-admin check (optional - will continue if admin elevation fails)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== Device Health Monitor起動 ===" -ForegroundColor Cyan
Write-Host ""

# ディレクトリ移動
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Python環境確認
Write-Host "[1/3] Python環境を確認中..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Pythonが見つかりません" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# 依存パッケージ確認
Write-Host "[2/3] 依存パッケージを確認中..." -ForegroundColor Yellow
$requiredPackages = @("psutil", "requests", "watchdog")
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

# 監視システム起動
Write-Host "[3/3] Device Health Monitorを起動中..." -ForegroundColor Yellow
Write-Host ""

# 通知機能付きで起動
python device_monitor_with_notifications.py

Write-Host ""
Write-Host "Device Health Monitorが停止しました" -ForegroundColor Cyan

