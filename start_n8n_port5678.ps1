# n8n起動スクリプト（ポート5678）

Write-Host "n8n起動中..." -ForegroundColor Cyan
Write-Host ""

$n8nPort = if ($env:N8N_PORT) { $env:N8N_PORT } else { "5678" }
$n8nBaseUrl = if ($env:N8N_URL) { $env:N8N_URL.TrimEnd('/') } else { "http://127.0.0.1:$n8nPort" }

# ポート確認
$portInUse = Get-NetTCPConnection -LocalPort ([int]$n8nPort) -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port $n8nPort is already in use" -ForegroundColor Yellow
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
$env:N8N_PORT = $n8nPort

Write-Host ""
Write-Host "Starting n8n on port $n8nPort..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Open in browser:" -ForegroundColor Yellow
Write-Host "  $n8nBaseUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# n8nを起動
n8n start --port $n8nPort


