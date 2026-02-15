# n8nを再起動するスクリプト

Write-Host "n8nの状態を確認しています..." -ForegroundColor Cyan

$n8nPort = if ($env:N8N_PORT) { $env:N8N_PORT } else { "5679" }
$n8nBaseUrl = if ($env:N8N_URL) { $env:N8N_URL.TrimEnd('/') } else { "http://127.0.0.1:$n8nPort" }

# ポートを使用しているプロセスを確認
$port = Get-NetTCPConnection -LocalPort ([int]$n8nPort) -ErrorAction SilentlyContinue
if ($port) {
    $pid = $port.OwningProcess
    Write-Host "ポート$n8nPort を使用しているプロセスID: $pid" -ForegroundColor Yellow
    
    # プロセスを終了
    Write-Host "n8nプロセスを終了しています..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# n8nを再起動
Write-Host "n8nを起動しています..." -ForegroundColor Cyan
Write-Host "ブラウザで $n8nBaseUrl を開いてください" -ForegroundColor Yellow
Write-Host "停止するには Ctrl+C を押してください" -ForegroundColor Gray
Write-Host ""

$env:N8N_PORT = $n8nPort
n8n start --port $n8nPort













