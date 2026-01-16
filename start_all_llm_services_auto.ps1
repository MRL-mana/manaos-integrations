# LLMルーティングシステム 全サービス起動スクリプト（自動版）

Write-Host "=" * 60
Write-Host "LLMルーティングシステム 全サービス起動（自動）"
Write-Host "=" * 60
Write-Host ""

$workDir = Get-Location
$pythonPath = "python"

# 1. LLMルーティングAPIを起動
Write-Host "[1] LLMルーティングAPIを起動中..." -ForegroundColor Yellow

# 既存のプロセスを停止
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*manaos_llm_routing_api*"
} | ForEach-Object {
    Write-Host "   既存のプロセスを停止: PID $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# 新しいプロセスを起動
$llmApiProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; `$env:PYTHONIOENCODING='utf-8'; python manaos_llm_routing_api.py" -WindowStyle Minimized -PassThru
Write-Host "   [OK] LLMルーティングAPIを起動しました (PID: $($llmApiProcess.Id))" -ForegroundColor Green
Start-Sleep -Seconds 5

# 2. 統合APIサーバーを起動
Write-Host ""
Write-Host "[2] 統合APIサーバーを起動中..." -ForegroundColor Yellow

# 既存のプロセスを停止
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*unified_api_server*"
} | ForEach-Object {
    Write-Host "   既存のプロセスを停止: PID $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# 新しいプロセスを起動
$unifiedApiProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; `$env:PYTHONIOENCODING='utf-8'; python unified_api_server.py" -WindowStyle Minimized -PassThru
Write-Host "   [OK] 統合APIサーバーを起動しました (PID: $($unifiedApiProcess.Id))" -ForegroundColor Green
Start-Sleep -Seconds 5

# 3. 起動確認
Write-Host ""
Write-Host "[3] 起動確認中..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$allOk = $true

# LLMルーティングAPI
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9501/api/llm/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   [OK] LLMルーティングAPI: 起動中" -ForegroundColor Green
    $status = $response.Content | ConvertFrom-Json
    Write-Host "      ステータス: $($status.status)" -ForegroundColor Gray
    Write-Host "      LLMサーバー: $($status.llm_server)" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] LLMルーティングAPI: 起動失敗または応答なし" -ForegroundColor Red
    Write-Host "      エラー: $($_.Exception.Message)" -ForegroundColor Gray
    $allOk = $false
}

# 統合APIサーバー
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9500/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   [OK] 統合APIサーバー: 起動中" -ForegroundColor Green
    $status = $response.Content | ConvertFrom-Json
    Write-Host "      ステータス: $($status.status)" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] 統合APIサーバー: 起動失敗または応答なし" -ForegroundColor Red
    Write-Host "      エラー: $($_.Exception.Message)" -ForegroundColor Gray
    $allOk = $false
}

Write-Host ""
Write-Host "=" * 60
if ($allOk) {
    Write-Host "✅ すべてのサービスが起動しました" -ForegroundColor Green
} else {
    Write-Host "⚠️  一部のサービスが起動していません" -ForegroundColor Yellow
    Write-Host "   もう少し待ってから .\check_running_status.ps1 で確認してください" -ForegroundColor Gray
}
Write-Host "=" * 60
Write-Host ""
Write-Host "実行中のプロセス:" -ForegroundColor Cyan
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*manaos_llm_routing*" -or $cmdLine -like "*unified_api_server*"
} | ForEach-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    Write-Host "  PID $($_.Id): $($cmdLine.Substring(0, [Math]::Min(80, $cmdLine.Length)))..." -ForegroundColor Gray
}
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  - LM Studioを起動してサーバーを開始" -ForegroundColor Gray
Write-Host "  - 状態確認: .\check_running_status.ps1" -ForegroundColor Gray
Write-Host "  - 常時起動設定: .\setup_llm_routing_autostart.ps1" -ForegroundColor Gray
Write-Host ""



















