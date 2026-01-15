# 統合APIサーバーを再起動するスクリプト

Write-Host "統合APIサーバーを再起動します..." -ForegroundColor Cyan

# ポート9500を使用しているプロセスを確認
$port = 9500
$processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    Write-Host "ポート $port を使用しているプロセスを停止します..." -ForegroundColor Yellow
    foreach ($procId in $processes) {
        if ($procId -ne 0) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "  プロセス $procId を停止しました" -ForegroundColor Green
        }
    }
    Start-Sleep -Seconds 2
}

# サーバーを起動
Write-Host "統合APIサーバーを起動します..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python start_server_direct.py" -WindowStyle Normal

Write-Host "統合APIサーバーを起動しました" -ForegroundColor Green
Write-Host "数秒待ってから http://localhost:9500/api/integrations/status で状態を確認してください" -ForegroundColor Cyan



