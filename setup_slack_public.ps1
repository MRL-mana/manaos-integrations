# Slack Integration公開設定スクリプト（ngrok経由）

Write-Host "=== Slack Integration公開設定（ngrok経由） ===" -ForegroundColor Cyan

$slackPort = if ($env:SLACK_API_PORT) { [int]$env:SLACK_API_PORT } else { 5114 }
$fileSecretaryPort = if ($env:FILE_SECRETARY_PORT) { [int]$env:FILE_SECRETARY_PORT } else { 5120 }
$orchestratorPort = if ($env:ORCHESTRATOR_PORT) { [int]$env:ORCHESTRATOR_PORT } else { 5106 }
$ngrokPort = if ($env:NGROK_PORT) { [int]$env:NGROK_PORT } else { 4040 }
$slackBaseUrl = if ($env:SLACK_API_URL) { $env:SLACK_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$slackPort" }
$fileSecretaryBaseUrl = if ($env:FILE_SECRETARY_URL) { $env:FILE_SECRETARY_URL.TrimEnd('/') } else { "http://127.0.0.1:$fileSecretaryPort" }
$orchestratorBaseUrl = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL.TrimEnd('/') } else { "http://127.0.0.1:$orchestratorPort" }
$ngrokBaseUrl = if ($env:NGROK_URL) { $env:NGROK_URL.TrimEnd('/') } else { "http://127.0.0.1:$ngrokPort" }

# 1. Verification Token確認
Write-Host "`n[1/4] Verification Token確認中..." -ForegroundColor Yellow
$verificationToken = $env:SLACK_VERIFICATION_TOKEN

if (-not $verificationToken) {
    Write-Host "  [WARN] SLACK_VERIFICATION_TOKENが設定されていません" -ForegroundColor Yellow
    Write-Host "`n  Verification Tokenの取得方法:" -ForegroundColor Cyan
    Write-Host "  1. https://api.slack.com/apps にアクセス" -ForegroundColor White
    Write-Host "  2. あなたのSlack Appを選択" -ForegroundColor White
    Write-Host "  3. 「Basic Information」→「App Credentials」" -ForegroundColor White
    Write-Host "  4. 「Verification Token」をコピー" -ForegroundColor White
    Write-Host "`n  取得後、以下を実行してください:" -ForegroundColor Yellow
    Write-Host "  `$env:SLACK_VERIFICATION_TOKEN = 'your_token'" -ForegroundColor White
    Write-Host "`n  続行しますか？ (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "  中断しました" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [OK] Verification Tokenが設定されています" -ForegroundColor Green
}

# 2. Slack Integration起動確認
Write-Host "`n[2/4] Slack Integration起動確認中..." -ForegroundColor Yellow
$slackRunning = Test-NetConnection -ComputerName 127.0.0.1 -Port $slackPort -WarningAction SilentlyContinue -InformationLevel Quiet -ErrorAction SilentlyContinue

if (-not $slackRunning) {
    Write-Host "  [WARN] Slack Integrationが起動していません" -ForegroundColor Yellow
    Write-Host "  起動しますか？ (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host "  Slack Integrationを起動中..." -ForegroundColor Yellow
        $config = Get-Content "notification_hub_enhanced_config.json" | ConvertFrom-Json
        $env:SLACK_WEBHOOK_URL = $config.slack_webhook_url
        $env:PORT = "$slackPort"
        $env:FILE_SECRETARY_URL = $fileSecretaryBaseUrl
        $env:ORCHESTRATOR_URL = $orchestratorBaseUrl
        Start-Process python -ArgumentList "slack_integration.py" -WindowStyle Normal
        Start-Sleep -Seconds 3
        Write-Host "  [OK] Slack Integrationを起動しました" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] Slack Integrationが起動しています" -ForegroundColor Green
}

# 3. ngrok確認
Write-Host "`n[3/4] ngrok確認中..." -ForegroundColor Yellow
$ngrokProcess = Get-Process ngrok -ErrorAction SilentlyContinue

if (-not $ngrokProcess) {
    Write-Host "  [WARN] ngrokが起動していません" -ForegroundColor Yellow
    Write-Host "`n  ngrokの起動方法:" -ForegroundColor Cyan
    Write-Host "  1. 新しいPowerShellウィンドウを開く" -ForegroundColor White
    Write-Host "  2. 以下を実行: ngrok http $slackPort" -ForegroundColor White
    Write-Host "  3. 表示されたURLをコピー（例: https://xxxx-xxxx-xxxx.ngrok.io）" -ForegroundColor White
    Write-Host "`n  ngrokを起動しますか？ (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host "  ngrokを起動中..." -ForegroundColor Yellow
        Start-Process ngrok -ArgumentList "http", "$slackPort" -WindowStyle Normal
        Start-Sleep -Seconds 3
        Write-Host "  [OK] ngrokを起動しました" -ForegroundColor Green
        Write-Host "  ngrokのWeb UI: $ngrokBaseUrl" -ForegroundColor Cyan
    }
} else {
    Write-Host "  [OK] ngrokが起動しています" -ForegroundColor Green
    Write-Host "  ngrokのWeb UI: $ngrokBaseUrl" -ForegroundColor Cyan
}

# 4. Slack App設定手順
Write-Host "`n[4/4] Slack App設定手順" -ForegroundColor Yellow
Write-Host "`n次の手順でSlack Appを設定してください:" -ForegroundColor Cyan
Write-Host "`n1. ngrokのURLを確認" -ForegroundColor White
Write-Host "   - ngrokのWeb UI: $ngrokBaseUrl" -ForegroundColor Gray
Write-Host "   - または: ngrokのターミナルに表示されたURL" -ForegroundColor Gray
Write-Host "`n2. Slack Appの設定" -ForegroundColor White
Write-Host "   - https://api.slack.com/apps にアクセス" -ForegroundColor Gray
Write-Host "   - あなたのSlack Appを選択" -ForegroundColor Gray
Write-Host "   - 「Event Subscriptions」を開く" -ForegroundColor Gray
Write-Host "   - 「Enable Events」をONにする" -ForegroundColor Gray
Write-Host "   - 「Request URL」に以下を設定:" -ForegroundColor Gray
Write-Host "     https://xxxx-xxxx-xxxx.ngrok.io/api/slack/events" -ForegroundColor Yellow
Write-Host "`n3. Subscribe to bot events" -ForegroundColor White
Write-Host "   - 「app_mentions」を追加" -ForegroundColor Gray
Write-Host "   - 「message.im」を追加（DM用）" -ForegroundColor Gray
Write-Host "`n4. Verification Token設定" -ForegroundColor White
Write-Host "   - 「Basic Information」→「App Credentials」" -ForegroundColor Gray
Write-Host "   - 「Verification Token」をコピー" -ForegroundColor Gray
Write-Host "   - 環境変数に設定: `$env:SLACK_VERIFICATION_TOKEN = 'your_token'" -ForegroundColor Gray
Write-Host "   - Slack Integrationを再起動" -ForegroundColor Gray

Write-Host "`n=== 設定完了 ===" -ForegroundColor Cyan
Write-Host "`n動作確認:" -ForegroundColor Yellow
Write-Host "  1. SlackでBotにメンション: @bot_name こんにちは" -ForegroundColor White
Write-Host "  2. BotにDM: こんにちは" -ForegroundColor White
Write-Host "  3. 返信が来るか確認" -ForegroundColor White
