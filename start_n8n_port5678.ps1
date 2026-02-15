# n8n起動スクリプト（ポート5678）

Write-Host "n8n起動中..." -ForegroundColor Cyan
Write-Host ""

# ポート5678の確認
$portInUse = Get-NetTCPConnection -LocalPort 5678 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port 5678 is already in use" -ForegroundColor Yellow
    Write-Host "Kill existing process? (y/n)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -eq "y") {
        $pid = $portInUse.OwningProcess
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "OK: Process killed" -ForegroundColor Green
    }
}

# データディレクトリの確認
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
    Write-Host "OK: Created data directory: $n8nDataDir" -ForegroundColor Green
}

# 環境変数を設定
$env:N8N_USER_FOLDER = $n8nDataDir
$env:N8N_PORT = "5678"

Write-Host ""
Write-Host "Starting n8n on port 5678..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Open in browser:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:5678" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# n8nを起動
n8n start --port 5678


