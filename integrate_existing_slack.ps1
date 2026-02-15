# 既存のSlack設定を統合してSlack Integrationを起動

Write-Host "=== 既存のSlack設定を統合 ===" -ForegroundColor Green
Write-Host ""

$slackPort = if ($env:SLACK_INTEGRATION_PORT) { $env:SLACK_INTEGRATION_PORT } else { "5114" }
$fileSecretaryPort = if ($env:FILE_SECRETARY_PORT) { $env:FILE_SECRETARY_PORT } else { "5120" }
$orchestratorPort = if ($env:ORCHESTRATOR_PORT) { $env:ORCHESTRATOR_PORT } else { "5106" }

$slackBaseUrl = if ($env:SLACK_API_URL) { $env:SLACK_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$slackPort" }
$fileSecretaryBaseUrl = if ($env:FILE_SECRETARY_URL) { $env:FILE_SECRETARY_URL.TrimEnd('/') } else { "http://127.0.0.1:$fileSecretaryPort" }
$orchestratorBaseUrl = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL.TrimEnd('/') } else { "http://127.0.0.1:$orchestratorPort" }

# Webhook URLを取得
$webhookUrl = $env:SLACK_WEBHOOK_URL
if (-not $webhookUrl) {
    Write-Host "❌ SLACK_WEBHOOK_URL が未設定です（Webhook URLを直書きしない方針です）" -ForegroundColor Red
    Write-Host "   例: [Environment]::SetEnvironmentVariable('SLACK_WEBHOOK_URL','https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>','User')" -ForegroundColor Gray
    exit 1
}

# 環境変数を設定
$env:SLACK_WEBHOOK_URL = $webhookUrl
$env:PORT = $slackPort
$env:FILE_SECRETARY_URL = $fileSecretaryBaseUrl
$env:ORCHESTRATOR_URL = $orchestratorBaseUrl

Write-Host "設定完了:" -ForegroundColor Cyan
Write-Host "  SLACK_WEBHOOK_URL: 設定済み"
Write-Host "  PORT: 5114"
Write-Host "  FILE_SECRETARY_URL: $fileSecretaryBaseUrl"
Write-Host "  ORCHESTRATOR_URL: $orchestratorBaseUrl"
Write-Host ""

# 既存のSlack Integrationプロセスを確認
$existingProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*slack_integration.py*"
}

if ($existingProcess) {
    Write-Host "既存のSlack Integrationプロセスを停止します..." -ForegroundColor Yellow
    $existingProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Slack Integrationを起動
Write-Host "Slack Integrationを起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "slack_integration.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# ヘルスチェック
Write-Host ""
Write-Host "ヘルスチェック中..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$slackBaseUrl/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Slack Integration起動成功！" -ForegroundColor Green
    Write-Host "   ステータス: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "⚠️ Slack Integrationの起動確認に失敗しました" -ForegroundColor Yellow
    Write-Host "   エラー: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 統合完了 ===" -ForegroundColor Green
Write-Host ""
Write-Host "SlackからFile Secretaryを使用できます:" -ForegroundColor Cyan
Write-Host "  - Inboxどう？ (INBOX状況確認)"
Write-Host "  - 終わった (ファイル整理)"
Write-Host "  - 戻して (ファイル復元)"
Write-Host "  - 探して：◯◯ (ファイル検索)"
Write-Host ""






















