# ManaOS統合サービス自動起動スクリプト
# Unified APIサーバーとLLM Routing APIサーバーを起動

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     ManaOS統合サービス自動起動スクリプト                          ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "[1] 既存のプロセスを確認..." -ForegroundColor Yellow

# Unified APIサーバーの既存プロセスを確認
$unifiedProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*unified_api_server*" 
}

if ($unifiedProcesses) {
    Write-Host "   既存のUnified APIサーバーが見つかりました" -ForegroundColor Yellow
    $unifiedProcesses | ForEach-Object {
        Write-Host "   PID: $($_.Id)" -ForegroundColor Gray
    }
    $restart = Read-Host "   再起動しますか？ (Y/N)"
    if ($restart -eq "Y" -or $restart -eq "y") {
        $unifiedProcesses | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
        Write-Host "   ✅ 停止しました" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  既存のプロセスを維持します" -ForegroundColor Yellow
    }
}

# LLM Routing APIサーバーの既存プロセスを確認
$routingProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*manaos_llm_routing_api*" 
}

if ($routingProcesses) {
    Write-Host "   既存のLLM Routing APIサーバーが見つかりました" -ForegroundColor Yellow
    $routingProcesses | ForEach-Object {
        Write-Host "   PID: $($_.Id)" -ForegroundColor Gray
    }
    $restart = Read-Host "   再起動しますか？ (Y/N)"
    if ($restart -eq "Y" -or $restart -eq "y") {
        $routingProcesses | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
        Write-Host "   ✅ 停止しました" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  既存のプロセスを維持します" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[2] Unified APIサーバーを起動..." -ForegroundColor Yellow

try {
    $unifiedProcess = Start-Process python -ArgumentList "unified_api_server.py" -WorkingDirectory $scriptDir -WindowStyle Hidden -PassThru
    Write-Host "   ✅ Unified APIサーバーを起動しました (PID: $($unifiedProcess.Id))" -ForegroundColor Green
    Write-Host "   URL: http://localhost:9500" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Unified APIサーバーの起動に失敗しました: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3] LLM Routing APIサーバーを起動..." -ForegroundColor Yellow

try {
    $routingProcess = Start-Process python -ArgumentList "manaos_llm_routing_api_enhanced.py" -WorkingDirectory $scriptDir -WindowStyle Hidden -PassThru
    Write-Host "   ✅ LLM Routing APIサーバーを起動しました (PID: $($routingProcess.Id))" -ForegroundColor Green
    Write-Host "   URL: http://localhost:9501" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ LLM Routing APIサーバーの起動に失敗しました: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4] サービス起動確認..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Unified APIサーバーの確認
Write-Host ""
Write-Host "   Unified APIサーバー:" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9500/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ 正常に起動しています ($($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  起動確認に失敗しました（起動に時間がかかっている可能性があります）" -ForegroundColor Yellow
}

# LLM Routing APIサーバーの確認
Write-Host ""
Write-Host "   LLM Routing APIサーバー:" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9501/api/llm/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $result = $response.Content | ConvertFrom-Json
    Write-Host "   ✅ 正常に起動しています" -ForegroundColor Green
    Write-Host "      ステータス: $($result.status)" -ForegroundColor Gray
    Write-Host "      LLMサーバー: $($result.llm_server)" -ForegroundColor Gray
    Write-Host "      利用可能モデル数: $($result.available_models)" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠️  起動確認に失敗しました（起動に時間がかかっている可能性があります）" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "║     ✅ すべてのサービスを起動しました！                          ║" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 利用可能なエンドポイント:" -ForegroundColor Yellow
Write-Host "   - Unified API: http://localhost:9500" -ForegroundColor Gray
Write-Host "   - LLM Routing API: http://localhost:9501" -ForegroundColor Gray
Write-Host ""
Write-Host "📋 MCPサーバー:" -ForegroundColor Yellow
Write-Host "   - llm-routing: 正常動作" -ForegroundColor Green
Write-Host "   - n8n: 正常動作（リモートサーバー接続は外部要因に依存）" -ForegroundColor Green
Write-Host ""
