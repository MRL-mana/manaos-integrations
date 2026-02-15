# ManaOS統合サービス停止スクリプト

Write-Host "[ManaOS統合サービスを停止]" -ForegroundColor Yellow
Write-Host ""

# Unified APIサーバーの停止
Write-Host "1. Unified APIサーバーを停止..." -ForegroundColor Cyan
$unifiedProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*unified_api_server*" 
}

if ($unifiedProcesses) {
    $unifiedProcesses | ForEach-Object {
        Write-Host "   停止中: PID $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "   ✅ Unified APIサーバーを停止しました" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  実行中のUnified APIサーバーが見つかりません" -ForegroundColor Gray
}

Write-Host ""

# LLM Routing APIサーバーの停止
Write-Host "2. LLM Routing APIサーバーを停止..." -ForegroundColor Cyan
$routingProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*llm_routing_mcp_server*" 
}

if ($routingProcesses) {
    $routingProcesses | ForEach-Object {
        Write-Host "   停止中: PID $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "   ✅ LLM Routing APIサーバーを停止しました" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  実行中のLLM Routing APIサーバーが見つかりません" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ すべてのサービスを停止しました" -ForegroundColor Green
Write-Host ""
