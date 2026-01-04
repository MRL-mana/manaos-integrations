# 統合APIサーバーを再起動するスクリプト

Write-Host "統合APIサーバーを再起動します..." -ForegroundColor Cyan

# ポート9500を使用しているプロセスを確認
$port = 9500
$processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    Write-Host "ポート $port を使用しているプロセスを停止します..." -ForegroundColor Yellow
    foreach ($pid in $processes) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "  プロセス $pid を停止しました" -ForegroundColor Green
    }
    Start-Sleep -Seconds 2
}

# サーバーを起動
Write-Host "統合APIサーバーを起動します..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python start_server_simple.py" -WindowStyle Normal

Write-Host "統合APIサーバーを起動しました" -ForegroundColor Green
Write-Host "数秒待ってから http://localhost:9500/api/integrations/status で状態を確認してください" -ForegroundColor Cyan



