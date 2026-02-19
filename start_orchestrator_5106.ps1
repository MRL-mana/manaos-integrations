# Unified Orchestrator (5106) 起動 - ManaOS をオンライン表示にする
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$port = 5106
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "Unified Orchestrator は既に起動中です (ポート $port)." -ForegroundColor Green
    exit 0
} catch {}

Start-Process python -ArgumentList "unified_orchestrator.py" -WindowStyle Hidden -WorkingDirectory $scriptDir
Start-Sleep -Seconds 3
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Unified Orchestrator を起動しました (http://127.0.0.1:$port)" -ForegroundColor Green
} catch {
    Write-Host "起動を開始しました。数秒後に http://127.0.0.1:$port/health で確認してください。" -ForegroundColor Yellow
}
