# 通知システム設定スクリプト
# 既存のSlack設定を読み込んで、新システムに統合

# Auto-admin check (optional - will continue if admin elevation fails)
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== 通知システム設定 ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. 既存のSlack設定を確認
Write-Host "[1/4] 既存のSlack設定を確認中..." -ForegroundColor Yellow

$slackWebhookUrl = $null

# 環境変数から取得
if ($env:SLACK_WEBHOOK_URL) {
    $slackWebhookUrl = $env:SLACK_WEBHOOK_URL
    Write-Host "[OK] 環境変数からSlack Webhook URLを取得しました" -ForegroundColor Green
}

# notification_system_state.jsonから取得
if (-not $slackWebhookUrl) {
    $stateFile = Join-Path $scriptDir "notification_system_state.json"
    if (Test-Path $stateFile) {
        try {
            $state = Get-Content $stateFile | ConvertFrom-Json
            if ($state.slack_webhook_url) {
                $slackWebhookUrl = $state.slack_webhook_url
                Write-Host "[OK] notification_system_state.jsonからSlack Webhook URLを取得しました" -ForegroundColor Green
            }
        } catch {
            Write-Host "[WARNING] notification_system_state.jsonの読み込みエラー" -ForegroundColor Yellow
        }
    }
}

# 2. Slack Webhook URLの入力
if (-not $slackWebhookUrl) {
    Write-Host "[2/4] Slack Webhook URLを入力してください" -ForegroundColor Yellow
    Write-Host "（既存のURLがある場合は入力、新規取得の場合はEnter）" -ForegroundColor Gray
    $input = Read-Host "Slack Webhook URL"
    
    if ($input) {
        $slackWebhookUrl = $input
    } else {
        Write-Host ""
        Write-Host "Slack Webhook URLの取得方法:" -ForegroundColor Cyan
        Write-Host "1. https://api.slack.com/apps にアクセス"
        Write-Host "2. アプリを選択（または新規作成）"
        Write-Host "3. Incoming Webhooks > Add New Webhook to Workspace"
        Write-Host "4. チャンネルを選択してWebhook URLをコピー"
        Write-Host ""
        $slackWebhookUrl = Read-Host "取得したSlack Webhook URLを入力してください"
    }
}

# 3. Notification Hub Enhanced設定を更新
Write-Host "[3/4] Notification Hub Enhanced設定を更新中..." -ForegroundColor Yellow

$configFile = Join-Path $scriptDir "notification_hub_enhanced_config.json"

if (Test-Path $configFile) {
    $config = Get-Content $configFile | ConvertFrom-Json
} else {
    # デフォルト設定を作成
    $config = @{
        slack_webhook_url = $null
        telegram_bot_token = $null
        telegram_chat_id = $null
        email = @{
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            username = $null
            password = $null
            from_address = $null
            to_addresses = @()
        }
        rules = @(
            @{
                name = "Critical Alerts"
                priority = "critical"
                channels = @("slack", "telegram", "email")
                conditions = @{ status = "critical" }
                enabled = $true
            }
        )
        history_file = "notification_history.json"
        max_history = 1000
    } | ConvertTo-Json -Depth 10 | ConvertFrom-Json
}

# Slack Webhook URLを設定
$config.slack_webhook_url = $slackWebhookUrl

# 設定を保存
$config | ConvertTo-Json -Depth 10 | Set-Content $configFile -Encoding UTF8
Write-Host "[OK] Notification Hub Enhanced設定を更新しました" -ForegroundColor Green

# 4. 既存のNotificationSystemにも設定
Write-Host "[4/4] 既存のNotificationSystem設定を更新中..." -ForegroundColor Yellow

$stateFile = Join-Path $scriptDir "notification_system_state.json"
$state = @{
    slack_webhook_url = $slackWebhookUrl
    discord_webhook_url = $null
    email_config = @{}
    history = @()
    last_updated = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
}

if (Test-Path $stateFile) {
    try {
        $existingState = Get-Content $stateFile | ConvertFrom-Json
        $state.discord_webhook_url = $existingState.discord_webhook_url
        $state.email_config = $existingState.email_config
        $state.history = $existingState.history
    } catch {
        # 既存ファイルの読み込みエラーは無視
    }
}

$state | ConvertTo-Json -Depth 10 | Set-Content $stateFile -Encoding UTF8
Write-Host "[OK] NotificationSystem設定を更新しました" -ForegroundColor Green

# 5. テスト通知を送信
Write-Host ""
Write-Host "テスト通知を送信しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
$testResponse = Read-Host

if ($testResponse -eq "Y" -or $testResponse -eq "y") {
    Write-Host "テスト通知を送信中..." -ForegroundColor Yellow
    
    try {
        $body = @{
            text = "✅ ManaOS通知システムの設定が完了しました！"
            username = "ManaOS Notification"
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest -Uri $slackWebhookUrl -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] テスト通知が送信されました！" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] テスト通知の送信に失敗しました（ステータスコード: $($response.StatusCode)）" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR] テスト通知の送信エラー: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== 設定完了 ===" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "1. Device Health Monitorを起動: .\start_device_monitoring.ps1"
Write-Host "2. 通知が正常に動作するか確認"
Write-Host ""

