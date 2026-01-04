# 緊急操作パネル用統合APIサーバー起動スクリプト
# 新PC（母艦）で実行

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "緊急操作パネル サーバー起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 現在のディレクトリを確認
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverScript = Join-Path $scriptDir "unified_api_server.py"

Write-Host "サーバースクリプト: $serverScript" -ForegroundColor Gray
Write-Host ""

# ファイルの存在確認
if (-not (Test-Path $serverScript)) {
    Write-Host "❌ サーバースクリプトが見つかりません: $serverScript" -ForegroundColor Red
    exit 1
}

# ポート9500が使用中か確認
Write-Host "[1/3] ポート9500の確認..." -ForegroundColor Green
$portInUse = Get-NetTCPConnection -LocalPort 9500 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "  ⚠️  ポート9500は既に使用中です" -ForegroundColor Yellow
    Write-Host "     プロセス: $($portInUse.OwningProcess)" -ForegroundColor Gray
    
    $killProcess = Read-Host "既存のプロセスを終了しますか？ (Y/N)"
    if ($killProcess -eq "Y" -or $killProcess -eq "y") {
        try {
            Stop-Process -Id $portInUse.OwningProcess -Force
            Write-Host "  ✅ プロセスを終了しました" -ForegroundColor Green
            Start-Sleep -Seconds 2
        } catch {
            Write-Host "  ❌ プロセス終了に失敗: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠️  既存のプロセスを終了しませんでした。別のターミナルでサーバーが起動している可能性があります。" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✅ ポート9500は使用可能です" -ForegroundColor Green
}

Write-Host ""

# Pythonの確認
Write-Host "[2/3] Pythonの確認..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Pythonが見つかりません" -ForegroundColor Red
    Write-Host "     Pythonをインストールしてください" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# サーバー起動
Write-Host "[3/3] サーバー起動..." -ForegroundColor Green
Write-Host "  緊急パネルURL: http://localhost:9500/emergency" -ForegroundColor Cyan
Write-Host "  緊急パネルURL（Tailscale）: http://100.73.247.100:9500/emergency" -ForegroundColor Cyan
Write-Host ""
Write-Host "  サーバーを停止するには Ctrl+C を押してください" -ForegroundColor Yellow
Write-Host ""

try {
    # サーバーを起動
    Set-Location $scriptDir
    python unified_api_server.py
} catch {
    Write-Host "  ❌ サーバー起動エラー: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}



