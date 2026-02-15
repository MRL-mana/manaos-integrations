# n8nをバックグラウンドで起動するスクリプト

Write-Host "n8nをバックグラウンドで起動中..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$n8nPort = if ($env:N8N_PORT) { $env:N8N_PORT } else { "5679" }
$n8nBaseUrl = if ($env:N8N_URL) { $env:N8N_URL.TrimEnd('/') } else { "http://127.0.0.1:$n8nPort" }

# ポート確認
$portInUse = Get-NetTCPConnection -LocalPort ([int]$n8nPort) -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[OK] n8nは既に起動中です (ポート $n8nPort)" -ForegroundColor Green
    exit 0
}

# データディレクトリの確認
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
}

# 環境変数を設定
$env:N8N_USER_FOLDER = $n8nDataDir
$env:N8N_PORT = $n8nPort
$env:N8N_LICENSE_KEY = "b01a8246-6a35-4221-917e-b5b25028a21b"

# ログファイル
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir "n8n.log"
$errorLogFile = Join-Path $logDir "n8n_error.log"

# バックグラウンドで起動
Write-Host "n8nを起動しています..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:N8N_USER_FOLDER='$n8nDataDir'; `$env:N8N_PORT='$n8nPort'; `$env:N8N_LICENSE_KEY='b01a8246-6a35-4221-917e-b5b25028a21b'; n8n start --port $n8nPort" -WindowStyle Minimized

Start-Sleep -Seconds 5

# 起動確認
$portCheck = Get-NetTCPConnection -LocalPort ([int]$n8nPort) -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "[OK] n8nが起動しました" -ForegroundColor Green
    Write-Host "  URL: $n8nBaseUrl" -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] n8nの起動確認ができませんでした（起動に時間がかかる可能性があります）" -ForegroundColor Yellow
    Write-Host "  ログを確認してください: logs/n8n.log" -ForegroundColor Gray
}
