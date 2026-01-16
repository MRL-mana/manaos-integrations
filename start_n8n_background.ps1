# n8nをバックグラウンドで起動するスクリプト

Write-Host "n8nをバックグラウンドで起動中..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# ポート5679の確認
$portInUse = Get-NetTCPConnection -LocalPort 5679 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[OK] n8nは既に起動中です (ポート 5679)" -ForegroundColor Green
    exit 0
}

# データディレクトリの確認
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
}

# 環境変数を設定
$env:N8N_USER_FOLDER = $n8nDataDir
$env:N8N_PORT = "5679"
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
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:N8N_USER_FOLDER='$n8nDataDir'; `$env:N8N_PORT='5679'; `$env:N8N_LICENSE_KEY='b01a8246-6a35-4221-917e-b5b25028a21b'; n8n start --port 5679" -WindowStyle Minimized

Start-Sleep -Seconds 5

# 起動確認
$portCheck = Get-NetTCPConnection -LocalPort 5679 -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "[OK] n8nが起動しました" -ForegroundColor Green
    Write-Host "  URL: http://localhost:5679" -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] n8nの起動確認ができませんでした（起動に時間がかかる可能性があります）" -ForegroundColor Yellow
    Write-Host "  ログを確認してください: logs/n8n.log" -ForegroundColor Gray
}
