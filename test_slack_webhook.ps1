# Slack Webhook接続テストスクリプト

Write-Host "🧪 Slack Webhook接続テスト開始" -ForegroundColor Green
Write-Host ""

# Webhook URL入力
$webhookUrl = Read-Host "Slack Webhook URLを入力してください（またはEnterで環境変数から取得）"

if ([string]::IsNullOrWhiteSpace($webhookUrl)) {
    $webhookUrl = $env:SLACK_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhookUrl)) {
        Write-Host "❌ Webhook URLが設定されていません" -ForegroundColor Red
        Write-Host "   環境変数 SLACK_WEBHOOK_URL を設定するか、直接URLを入力してください" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ 環境変数から取得: $webhookUrl" -ForegroundColor Green
} else {
    Write-Host "✅ URLを入力: $webhookUrl" -ForegroundColor Green
}

Write-Host ""

# URL形式確認
if (-not $webhookUrl.StartsWith("https://hooks.slack.com/services/")) {
    Write-Host "⚠️  Webhook URLの形式が正しくない可能性があります" -ForegroundColor Yellow
    Write-Host "   正しい形式: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "続行しますか？ (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""

# テストメッセージ送信
Write-Host "📤 テストメッセージを送信中..." -ForegroundColor Yellow

$bodyObject = @{
    text = "テストメッセージ from ManaOS n8n Integration`n`nこれは接続テストです。"
}
$body = $bodyObject | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host ""
    Write-Host "✅ 成功！Slackにメッセージを送信しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "次のステップ:" -ForegroundColor Cyan
    Write-Host "1. Slackチャンネルを確認してください" -ForegroundColor White
    Write-Host "2. メッセージが届いていれば、n8nのHTTP Requestノードに同じURLを設定してください" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ エラーが発生しました" -ForegroundColor Red
    Write-Host ""
    Write-Host "エラー詳細:" -ForegroundColor Yellow
    Write-Host "  Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor White
    Write-Host "  Message: $($_.Exception.Message)" -ForegroundColor White
    Write-Host ""
    
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "💡 解決方法:" -ForegroundColor Cyan
        Write-Host "  - Webhook URLが無効です" -ForegroundColor White
        Write-Host "  - Slack AppでWebhook URLを再生成してください" -ForegroundColor White
        Write-Host "  - https://api.slack.com/apps → Incoming Webhooks" -ForegroundColor White
    } elseif ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Host "💡 解決方法:" -ForegroundColor Cyan
        Write-Host "  - Webhook URLが間違っています" -ForegroundColor White
        Write-Host "  - URLを確認してください" -ForegroundColor White
    } else {
        Write-Host "💡 解決方法:" -ForegroundColor Cyan
        Write-Host "  - ネットワーク接続を確認してください" -ForegroundColor White
        Write-Host "  - ファイアウォール設定を確認してください" -ForegroundColor White
        Write-Host "  - Webhook URLを再確認してください" -ForegroundColor White
    }
    
    exit 1
}

