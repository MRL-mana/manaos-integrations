# LLMルーティングシステム 全サービス起動スクリプト

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "=" * 60
Write-Host "LLMルーティングシステム 全サービス起動"
Write-Host "=" * 60
Write-Host ""

$workDir = Get-Location

# URL（環境変数で上書き可能）
$defaultUnifiedPort = if ($env:UNIFIED_API_PORT) { $env:UNIFIED_API_PORT } elseif ($env:PORT) { $env:PORT } else { "9502" }
$llmRoutingPort = if ($env:LLM_ROUTING_PORT) { $env:LLM_ROUTING_PORT } else { "5111" }
$unifiedApiBaseUrl = if ($env:MANAOS_INTEGRATION_API_URL) { $env:MANAOS_INTEGRATION_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$defaultUnifiedPort" }
$llmRoutingBaseUrl = if ($env:LLM_ROUTING_URL) { $env:LLM_ROUTING_URL.TrimEnd('/') } else { "http://127.0.0.1:$llmRoutingPort" }

function Get-UriSafe {
    param([string]$Url)
    try {
        return [uri]$Url
    } catch {
        return $null
    }
}

$unifiedApiUri = Get-UriSafe -Url $unifiedApiBaseUrl
$unifiedApiPort = if ($unifiedApiUri) { $unifiedApiUri.Port } else { $defaultUnifiedPort }

# 1. LLM Routing MCP を起動（ヘルス: 5111）
Write-Host "[1] LLM Routing MCP を起動中..." -ForegroundColor Yellow

# 既存のプロセスを確認
$existingProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*llm_routing_mcp_server*"
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
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; `$env:PYTHONIOENCODING='utf-8'; `$env:MANAOS_LOG_TO_STDERR='1'; python -m llm_routing_mcp_server" -WindowStyle Minimized
    Write-Host "   [OK] LLM Routing MCP を起動しました" -ForegroundColor Green
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
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; `$env:PYTHONIOENCODING='utf-8'; `$env:PORT='$unifiedApiPort'; py -3.10 unified_api_server.py" -WindowStyle Minimized
    Write-Host "   [OK] 統合APIサーバーを起動しました" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

# 3. 起動確認
Write-Host ""
Write-Host "[3] 起動確認中..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$allOk = $true

# LLM Routing MCP health
try {
    $status = Invoke-RestMethod -Uri "$llmRoutingBaseUrl/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [OK] LLM Routing MCP: 起動中" -ForegroundColor Green
} catch {
    Write-Host "   [NG] LLM Routing MCP: 起動失敗" -ForegroundColor Red
    $allOk = $false
}

# 統合APIサーバー
try {
    $status = Invoke-RestMethod -Uri "$unifiedApiBaseUrl/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [OK] 統合APIサーバー: 起動中" -ForegroundColor Green
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



















