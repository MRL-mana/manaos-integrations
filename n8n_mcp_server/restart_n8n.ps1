# n8nを再起動するスクリプト

Write-Host "n8nの状態を確認しています..." -ForegroundColor Cyan

# ポート5679を使用しているプロセスを確認
$port = Get-NetTCPConnection -LocalPort 5679 -ErrorAction SilentlyContinue
if ($port) {
    $pid = $port.OwningProcess
    Write-Host "ポート5679を使用しているプロセスID: $pid" -ForegroundColor Yellow
    
    # プロセスを終了
    Write-Host "n8nプロセスを終了しています..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# n8nを再起動
Write-Host "n8nを起動しています..." -ForegroundColor Cyan
Write-Host "ブラウザで http://127.0.0.1:5679 を開いてください" -ForegroundColor Yellow
Write-Host "停止するには Ctrl+C を押してください" -ForegroundColor Gray
Write-Host ""

$env:N8N_PORT = "5679"
n8n start --port 5679













