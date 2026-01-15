# File Secretary クイック起動スクリプト（Windows用）

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== File Secretary クイック起動 ===" -ForegroundColor Cyan
Write-Host ""

# 環境変数設定
$env:PORT = "5120"
$env:FILE_SECRETARY_DB_PATH = "file_secretary.db"
$env:INBOX_PATH = Join-Path $ScriptDir "00_INBOX"

# INBOXディレクトリ作成
if (-not (Test-Path $env:INBOX_PATH)) {
    New-Item -ItemType Directory -Path $env:INBOX_PATH -Force | Out-Null
    Write-Host "📁 INBOXディレクトリ作成完了" -ForegroundColor Green
}

# データベース初期化
Write-Host "📊 データベース初期化中..." -ForegroundColor Yellow
python -c "from file_secretary_db import FileSecretaryDB; FileSecretaryDB('file_secretary.db')" 2>&1 | Out-Null

# Indexer起動（バックグラウンド）
Write-Host "📂 Indexer起動中..." -ForegroundColor Yellow
$indexerJob = Start-Job -ScriptBlock {
    Set-Location $using:ScriptDir
    $env:INBOX_PATH = $using:env:INBOX_PATH
    $env:FILE_SECRETARY_DB_PATH = $using:env:FILE_SECRETARY_DB_PATH
    python file_secretary_start.py
}
Write-Host "✅ Indexer起動完了 (Job ID: $($indexerJob.Id))" -ForegroundColor Green

# APIサーバー起動（バックグラウンド）
Start-Sleep -Seconds 2
Write-Host "🔌 APIサーバー起動中..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:ScriptDir
    $env:PORT = $using:env:PORT
    $env:FILE_SECRETARY_DB_PATH = $using:env:FILE_SECRETARY_DB_PATH
    $env:INBOX_PATH = $using:env:INBOX_PATH
    python file_secretary_api.py
}
Write-Host "✅ APIサーバー起動完了 (Job ID: $($apiJob.Id))" -ForegroundColor Green

# 起動確認
Start-Sleep -Seconds 3
Write-Host ""
Write-Host "📊 状態確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5120/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ APIサーバー: 正常応答" -ForegroundColor Green
} catch {
    Write-Host "⚠️ APIサーバー: 応答なし" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ File Secretary 起動完了" -ForegroundColor Green
Write-Host ""
Write-Host "停止するには:" -ForegroundColor Cyan
Write-Host "  Stop-Job $($indexerJob.Id), $($apiJob.Id)"
Write-Host "  Remove-Job $($indexerJob.Id), $($apiJob.Id)"
Write-Host ""
Write-Host "状態確認:" -ForegroundColor Cyan
Write-Host "  Get-Job"
Write-Host ""
Write-Host "ログ確認:" -ForegroundColor Cyan
Write-Host "  Receive-Job $($indexerJob.Id)"
Write-Host "  Receive-Job $($apiJob.Id)"

# プロセスを待機
Write-Host ""
Write-Host "プロセス実行中... (Ctrl+Cで停止)" -ForegroundColor Yellow
try {
    Wait-Job $indexerJob, $apiJob
} catch {
    Write-Host "停止シグナルを受信しました" -ForegroundColor Yellow
    Stop-Job $indexerJob, $apiJob
    Remove-Job $indexerJob, $apiJob
}






















