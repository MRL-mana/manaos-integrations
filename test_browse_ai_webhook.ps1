# Browse AI Webhook Test Script

param(
    [string]$WebhookUrl = "http://localhost:5678/webhook-test/browse-ai-webhook"
)

Write-Host "Browse AI Webhook Test Start" -ForegroundColor Green
Write-Host ""
Write-Host "Webhook URL: $WebhookUrl" -ForegroundColor Cyan
Write-Host ""

# Create test data
$testData = @{
    robot = @{
        name = "Sale Monitor"
    }
    capturedAt = @{
        url = "https://example.com/product/123"
        timestamp = (Get-Date).ToString("o")
    }
    extractedData = @{
        name = "Test Product"
        price = "1000 yen"
        originalPrice = "1250 yen"
        discount = "20%"
        link = "https://example.com/product/123"
    }
}

$body = $testData | ConvertTo-Json -Depth 10

Write-Host "Sending test data..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Data:" -ForegroundColor Cyan
Write-Host $body -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host ""
    Write-Host "SUCCESS: Data sent to webhook" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Check n8n workflow" -ForegroundColor White
    Write-Host "2. Check Slack notification" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to send data" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Yellow
    if ($_.Exception.Response) {
        Write-Host "  Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor White
    }
    Write-Host "  Message: $($_.Exception.Message)" -ForegroundColor White
    Write-Host ""
    Write-Host "Check:" -ForegroundColor Cyan
    Write-Host "  - Is n8n running?" -ForegroundColor White
    Write-Host "  - Is webhook node listening?" -ForegroundColor White
    Write-Host "  - Is URL correct?" -ForegroundColor White
    exit 1
}

