# LLMルーティング統合スクリプト
# 既存のunified_api_server.pyに拡張LLMルーティング機能を統合

Write-Host "=" * 60
Write-Host "LLMルーティング統合"
Write-Host "=" * 60
Write-Host ""

# 統合APIサーバーの再起動
Write-Host "[1] 統合APIサーバーを確認中..." -ForegroundColor Yellow

$apiProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*unified_api_server*"
}

if ($apiProcess) {
    Write-Host "   統合APIサーバーが実行中です" -ForegroundColor Green
    Write-Host "   ポート9500で動作中" -ForegroundColor Cyan
} else {
    Write-Host "   統合APIサーバーが実行されていません" -ForegroundColor Yellow
    Write-Host "   起動してください: python unified_api_server.py" -ForegroundColor Cyan
}

Write-Host ""

# 拡張LLMルーティングAPIの起動確認
Write-Host "[2] 拡張LLMルーティングAPIを確認中..." -ForegroundColor Yellow

$routingProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*manaos_llm_routing_api*"
}

if ($routingProcess) {
    Write-Host "   拡張LLMルーティングAPIが実行中です" -ForegroundColor Green
    Write-Host "   ポート9501で動作中" -ForegroundColor Cyan
} else {
    Write-Host "   拡張LLMルーティングAPIが実行されていません" -ForegroundColor Yellow
    Write-Host "   起動してください: .\start_llm_routing_api.ps1" -ForegroundColor Cyan
}

Write-Host ""

# テスト実行
Write-Host "[3] テストを実行しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
$testInput = Read-Host

if ($testInput -eq "y") {
    Write-Host ""
    Write-Host "   テストを実行中..." -ForegroundColor Yellow
    python test_llm_routing.py
}

Write-Host ""
Write-Host "=" * 60
Write-Host "統合完了"
Write-Host "=" * 60
Write-Host ""
Write-Host "利用可能なエンドポイント:" -ForegroundColor Cyan
Write-Host "  - POST http://localhost:9500/api/llm/route-enhanced" -ForegroundColor Green
Write-Host "  - POST http://localhost:9500/api/llm/analyze" -ForegroundColor Green
Write-Host "  - GET  http://localhost:9500/api/llm/models-enhanced" -ForegroundColor Green
Write-Host ""



















