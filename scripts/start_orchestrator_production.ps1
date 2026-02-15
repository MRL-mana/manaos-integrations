# ask_orchestrator 本格運用スタート
# 5106 と Portal の起動確認 → 問題なければ「本格運用の土台は起動しています」と表示
# 使い方: .\scripts\start_orchestrator_production.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
Set-Location $rootDir

$orchestratorPort = if ($env:ORCHESTRATOR_PORT) { $env:ORCHESTRATOR_PORT } else { "5106" }
$portalPort = if ($env:PORTAL_INTEGRATION_PORT) { $env:PORTAL_INTEGRATION_PORT } else { "5108" }

if (-not $env:ORCHESTRATOR_URL) {
    $env:ORCHESTRATOR_URL = "http://127.0.0.1:$orchestratorPort"
}
if (-not $env:PORTAL_URL) {
    $env:PORTAL_URL = "http://127.0.0.1:$portalPort"
}

Write-Host "ask_orchestrator 本格運用 起動確認" -ForegroundColor Cyan
Write-Host ""

python scripts/check_orchestrator_production_ready.py
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "次のステップ:" -ForegroundColor Green
    Write-Host "  - Slack 通知: .env に SLACK_WEBHOOK_URL または SLACK_BOT_TOKEN を設定"
    Write-Host "  - 集計: GET $($env:PORTAL_URL)/api/orchestrator/stats"
    Write-Host "  - 事故防止テスト: python scripts/test_ask_orchestrator_safety.py"
}
exit $exitCode
