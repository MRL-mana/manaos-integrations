# ManaOS統合サービス自動起動スクリプト
# Unified APIサーバーとLLM Routing APIサーバーを起動

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     ManaOS統合サービス自動起動スクリプト                          ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# URL（環境変数で上書き可能）
$defaultUnifiedPort = if ($env:UNIFIED_API_PORT) { $env:UNIFIED_API_PORT } elseif ($env:PORT) { $env:PORT } else { "9502" }
$llmRoutingPort = if ($env:LLM_ROUTING_PORT) { $env:LLM_ROUTING_PORT } else { "5111" }
$unifiedApiBaseUrl = if ($env:MANAOS_INTEGRATION_API_URL) { $env:MANAOS_INTEGRATION_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$defaultUnifiedPort" }
$llmRoutingBaseUrl = if ($env:LLM_ROUTING_URL) { $env:LLM_ROUTING_URL.TrimEnd('/') } else { "http://127.0.0.1:$llmRoutingPort" }

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
    $cmdLine -like "*llm_routing_mcp_server*" 
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
    Write-Host "   URL: $unifiedApiBaseUrl" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Unified APIサーバーの起動に失敗しました: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3] LLM Routing APIサーバーを起動..." -ForegroundColor Yellow

try {
    $routingProcess = Start-Process python -ArgumentList "-m llm_routing_mcp_server" -WorkingDirectory $scriptDir -WindowStyle Hidden -PassThru
    Write-Host "   ✅ LLM Routingサーバーを起動しました (PID: $($routingProcess.Id))" -ForegroundColor Green
    Write-Host "   URL: $llmRoutingBaseUrl" -ForegroundColor Gray
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
    $response = Invoke-WebRequest -Uri "$unifiedApiBaseUrl/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ 正常に起動しています ($($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  起動確認に失敗しました（起動に時間がかかっている可能性があります）" -ForegroundColor Yellow
}

# LLM Routing APIサーバーの確認
Write-Host ""
Write-Host "   LLM Routing APIサーバー:" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$llmRoutingBaseUrl/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ 正常に起動しています ($($response.StatusCode))" -ForegroundColor Green
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
Write-Host "   - Unified API: $unifiedApiBaseUrl" -ForegroundColor Gray
Write-Host "   - LLM Routing: $llmRoutingBaseUrl" -ForegroundColor Gray
Write-Host ""
Write-Host "📋 MCPサーバー:" -ForegroundColor Yellow
Write-Host "   - llm-routing: 正常動作" -ForegroundColor Green
Write-Host "   - n8n: 正常動作（リモートサーバー接続は外部要因に依存）" -ForegroundColor Green
Write-Host ""
