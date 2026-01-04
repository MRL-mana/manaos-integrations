# Slack Webhook Test Script

param(
    [string]$WebhookUrl = ""
)

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $WebhookUrl = $env:SLACK_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        Write-Host "ERROR: Webhook URL not set"
        Write-Host "Usage: .\test_slack_simple.ps1 -WebhookUrl 'YOUR_WEBHOOK_URL'"
        Write-Host "Or set: `$env:SLACK_WEBHOOK_URL = 'YOUR_WEBHOOK_URL'"
        exit 1
    }
}

Write-Host "Testing Slack Webhook URL..."
Write-Host "URL: $WebhookUrl"
Write-Host ""

$body = '{"text":"Test message from ManaOS n8n Integration"}'

try {
    $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host "SUCCESS: Message sent to Slack!"
    Write-Host "Check your Slack channel for the test message."
} catch {
    Write-Host "ERROR: Failed to send message"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Message: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Troubleshooting:"
    Write-Host "1. Check if Webhook URL is correct"
    Write-Host "2. Check if Webhook is enabled in Slack App"
    Write-Host "3. Check network connection"
    exit 1
}


