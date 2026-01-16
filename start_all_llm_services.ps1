# LLMルーティングシステム 全サービス起動スクリプト

Write-Host "=" * 60
Write-Host "LLMルーティングシステム 全サービス起動"
Write-Host "=" * 60
Write-Host ""

$workDir = Get-Location

# 1. LLMルーティングAPIを起動
Write-Host "[1] LLMルーティングAPIを起動中..." -ForegroundColor Yellow

# 既存のプロセスを確認
$existingProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*manaos_llm_routing_api*"
}

if ($existingProcesses) {
    Write-Host "   [情報] 既に起動中のプロセスがあります" -ForegroundColor Yellow
    Write-Host "   停止して再起動しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
    $restart = Read-Host
    if ($restart -eq "y") {
        $existingProcesses | Stop-Process -Force
        Start-Sleep -Seconds 2
    } else {
        Write-Host "   既存のプロセスを使用します" -ForegroundColor Gray
    }
}

if (-not $existingProcesses -or $restart -eq "y") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; python manaos_llm_routing_api.py" -WindowStyle Minimized
    Write-Host "   [OK] LLMルーティングAPIを起動しました" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

# 2. 統合APIサーバーを起動
Write-Host ""
Write-Host "[2] 統合APIサーバーを起動中..." -ForegroundColor Yellow

# 既存のプロセスを確認
$existingUnified = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*unified_api_server*"
}

if ($existingUnified) {
    Write-Host "   [情報] 既に起動中のプロセスがあります" -ForegroundColor Yellow
    Write-Host "   停止して再起動しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
    $restartUnified = Read-Host
    if ($restartUnified -eq "y") {
        $existingUnified | Stop-Process -Force
        Start-Sleep -Seconds 2
    } else {
        Write-Host "   既存のプロセスを使用します" -ForegroundColor Gray
    }
}

if (-not $existingUnified -or $restartUnified -eq "y") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; python unified_api_server.py" -WindowStyle Minimized
    Write-Host "   [OK] 統合APIサーバーを起動しました" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

# 3. 起動確認
Write-Host ""
Write-Host "[3] 起動確認中..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$allOk = $true

# LLMルーティングAPI
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9501/api/llm/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [OK] LLMルーティングAPI: 起動中" -ForegroundColor Green
    $status = $response.Content | ConvertFrom-Json
    Write-Host "      ステータス: $($status.status)" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] LLMルーティングAPI: 起動失敗" -ForegroundColor Red
    $allOk = $false
}

# 統合APIサーバー
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9500/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [OK] 統合APIサーバー: 起動中" -ForegroundColor Green
    $status = $response.Content | ConvertFrom-Json
    Write-Host "      ステータス: $($status.status)" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] 統合APIサーバー: 起動失敗" -ForegroundColor Red
    $allOk = $false
}

Write-Host ""
Write-Host "=" * 60
if ($allOk) {
    Write-Host "✅ すべてのサービスが起動しました" -ForegroundColor Green
} else {
    Write-Host "⚠️  一部のサービスが起動していません" -ForegroundColor Yellow
    Write-Host "   詳細は .\check_running_status.ps1 で確認してください" -ForegroundColor Gray
}
Write-Host "=" * 60
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  - LM Studioを起動してサーバーを開始" -ForegroundColor Gray
Write-Host "  - 状態確認: .\check_running_status.ps1" -ForegroundColor Gray
Write-Host "  - 常時起動設定: .\setup_llm_routing_autostart.ps1" -ForegroundColor Gray
Write-Host ""



















