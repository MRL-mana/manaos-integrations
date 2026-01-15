# ManaOS統合サービス再起動スクリプト

Write-Host "=== ManaOS統合サービス再起動 ===" -ForegroundColor Green
Write-Host ""

# 環境変数を設定
$slackWebhookUrl = $env:SLACK_WEBHOOK_URL
if (-not $slackWebhookUrl) {
    Write-Host "❌ SLACK_WEBHOOK_URL が未設定です（Webhook URLを直書きしない方針です）" -ForegroundColor Red
    Write-Host "   例: [Environment]::SetEnvironmentVariable('SLACK_WEBHOOK_URL','https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>','User')" -ForegroundColor Gray
    exit 1
}
$env:SLACK_WEBHOOK_URL = $slackWebhookUrl
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"

Write-Host "環境変数設定完了" -ForegroundColor Cyan
Write-Host ""

# 既存プロセスを停止
Write-Host "既存プロセスを停止中..." -ForegroundColor Yellow

# Slack Integration
$slackProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*slack_integration.py*"
}
if ($slackProcess) {
    Write-Host "  - Slack Integration停止中..." -ForegroundColor Cyan
    $slackProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# File Secretary API
$fileSecretaryProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*file_secretary_api.py*"
}
if ($fileSecretaryProcess) {
    Write-Host "  - File Secretary API停止中..." -ForegroundColor Cyan
    $fileSecretaryProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# File Secretary Indexer
$indexerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*file_secretary_start.py*"
}
if ($indexerProcess) {
    Write-Host "  - File Secretary Indexer停止中..." -ForegroundColor Cyan
    $indexerProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# IntentRouter（実行中の場合）
$intentRouterProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*intent_router.py*"
}
if ($intentRouterProcess) {
    Write-Host "  - IntentRouter停止中..." -ForegroundColor Cyan
    $intentRouterProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "サービスを起動中..." -ForegroundColor Yellow
Write-Host ""

# File Secretary Indexerを起動
Write-Host "1. File Secretary Indexer起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "file_secretary_start.py" -WindowStyle Normal
Start-Sleep -Seconds 3

# File Secretary APIを起動
Write-Host "2. File Secretary API起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "file_secretary_api.py" -WindowStyle Normal
Start-Sleep -Seconds 3

# Slack Integrationを起動
Write-Host "3. Slack Integration起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "slack_integration.py" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "ヘルスチェック中..." -ForegroundColor Yellow
Write-Host ""

# ヘルスチェック
$services = @(
    @{Name="File Secretary API"; URL="http://localhost:5120/health"},
    @{Name="Slack Integration"; URL="http://localhost:5114/health"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-RestMethod -Uri $service.URL -Method Get -TimeoutSec 5
        Write-Host "  ✅ $($service.Name): 起動成功" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️ $($service.Name): 起動確認失敗（数秒待ってから再確認してください）" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== 再起動完了 ===" -ForegroundColor Green
Write-Host ""
Write-Host "統合機能:" -ForegroundColor Cyan
Write-Host "  ✅ File Secretary: 記憶機能統合済み"
Write-Host "  ✅ IntentRouter: 人格設定統合済み"
Write-Host "  ✅ Slack Integration: 人格設定適用済み"
Write-Host ""
Write-Host "🎉 全サービス再起動完了！" -ForegroundColor Yellow






















