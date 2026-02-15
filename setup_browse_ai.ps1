# Browse AI Integration Setup Script
# Recommended Order: Step 1 (Highest Priority)

Write-Host "🚀 Browse AI Integration Setup Started" -ForegroundColor Green
Write-Host ""

# n8n base URL（env優先）
$n8nBaseUrl = if ($env:N8N_URL) {
    $env:N8N_URL.TrimEnd('/')
} elseif ($env:N8N_PORT) {
    ("http://127.0.0.1:{0}" -f $env:N8N_PORT).TrimEnd('/')
} else {
    "http://127.0.0.1:5678"
}

# Step 1: n8n Check
Write-Host "📋 Step 1: Checking n8n..." -ForegroundColor Yellow
try {
    # Try to check if n8n is running (without auth for now)
    $response = Invoke-WebRequest -Uri $n8nBaseUrl -Method Get -ErrorAction Stop
    Write-Host "✅ n8n is running normally" -ForegroundColor Green
    Write-Host "   Access: $n8nBaseUrl" -ForegroundColor Cyan
    Write-Host "   Note: API may require authentication" -ForegroundColor Yellow
} catch {
    Write-Host "⚠️  Cannot connect to n8n" -ForegroundColor Yellow
    Write-Host "   Check: $n8nBaseUrl" -ForegroundColor Cyan
    Write-Host "   If n8n is not running, start it first" -ForegroundColor Yellow
    Write-Host "   Error: $_" -ForegroundColor Gray
}

Write-Host ""

# Step 2: Workflow File Check
Write-Host "📋 Step 2: Checking workflow file..." -ForegroundColor Yellow
$workflowPath = Join-Path $PSScriptRoot "n8n_workflows\browse_ai_manaos_integration.json"
if (Test-Path $workflowPath) {
    Write-Host "✅ Workflow file found" -ForegroundColor Green
    Write-Host "   Path: $workflowPath" -ForegroundColor Cyan
} else {
    Write-Host "❌ Workflow file not found" -ForegroundColor Red
    Write-Host "   Path: $workflowPath" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 3: Environment Variable Check
Write-Host "📋 Step 3: Checking environment variables..." -ForegroundColor Yellow
$slackWebhook = $env:SLACK_WEBHOOK_URL
if ($slackWebhook) {
    Write-Host "✅ SLACK_WEBHOOK_URL is set" -ForegroundColor Green
} else {
    Write-Host "⚠️  SLACK_WEBHOOK_URL is not set" -ForegroundColor Yellow
    Write-Host "   Setup method:" -ForegroundColor Cyan
    Write-Host "   1. Create Slack App: https://api.slack.com/apps" -ForegroundColor White
    Write-Host "   2. Enable Incoming Webhooks" -ForegroundColor White
    Write-Host "   3. Get Webhook URL" -ForegroundColor White
    Write-Host "   4. Set environment variable: `$env:SLACK_WEBHOOK_URL = 'your-webhook-url'" -ForegroundColor White
    Write-Host ""
    $setNow = Read-Host "Set now? (y/n)"
    if ($setNow -eq "y") {
        $webhookUrl = Read-Host "Enter Slack Webhook URL"
        $env:SLACK_WEBHOOK_URL = $webhookUrl
        Write-Host "✅ Environment variable set (valid for this session only)" -ForegroundColor Green
        Write-Host "   To make it permanent, set it as a system environment variable" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 4: Workflow Import Preparation
Write-Host "📋 Step 4: Workflow import preparation..." -ForegroundColor Yellow
Write-Host "   Follow these steps to import:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Method A: Via Portal UI (Recommended)" -ForegroundColor White
Write-Host "   1. Access Portal UI: http://127.0.0.1:5000" -ForegroundColor Gray
Write-Host "   2. Open n8n section" -ForegroundColor Gray
Write-Host "   3. Click 'Import Workflow'" -ForegroundColor Gray
Write-Host "   4. Select file: $workflowPath" -ForegroundColor Gray
Write-Host ""
Write-Host "   Method B: Via API" -ForegroundColor White
Write-Host "   curl -X POST $n8nBaseUrl/rest/workflows \" -ForegroundColor Gray
Write-Host "     -H 'Content-Type: application/json' \" -ForegroundColor Gray
Write-Host "     -d @$workflowPath" -ForegroundColor Gray
Write-Host ""

# Step 5: Browse AI Setup Check
Write-Host "📋 Step 5: Browse AI setup check..." -ForegroundColor Yellow
Write-Host "   Follow these steps to set up Browse AI:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Access Browse AI: https://www.browse.ai/" -ForegroundColor White
Write-Host "   2. Create account (Starter plan: `$49/month)" -ForegroundColor White
Write-Host "   3. Create new robot:" -ForegroundColor White
Write-Host "      - Name: 'CivitAI Sale Monitor'" -ForegroundColor Gray
Write-Host "      - URL: https://civitai.com/models?onSale=true" -ForegroundColor Gray
Write-Host "      - Monitor type: Change detection" -ForegroundColor Gray
Write-Host "   4. Webhook setup:" -ForegroundColor White
Write-Host "      - URL: $n8nBaseUrl/webhook/browse-ai-webhook" -ForegroundColor Gray
Write-Host "      - Or: Use ngrok for external access" -ForegroundColor Gray
Write-Host ""

# Step 6: Webhook URL Acquisition
Write-Host "📋 Step 6: Webhook URL acquisition..." -ForegroundColor Yellow
Write-Host "   After importing the workflow, the following URL will be the webhook endpoint:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Local: $n8nBaseUrl/webhook/browse-ai-webhook" -ForegroundColor White
Write-Host ""
Write-Host "   For external access (Recommended):" -ForegroundColor Yellow
Write-Host "   ngrok http 5678" -ForegroundColor White
Write-Host "   Use the obtained URL for Browse AI webhook setup" -ForegroundColor White
Write-Host ""

# Completion Message
Write-Host "✅ Setup preparation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Create Browse AI account (30 min)" -ForegroundColor White
Write-Host "2. Import n8n workflow (10 min)" -ForegroundColor White
Write-Host "3. Set up Browse AI (30 min)" -ForegroundColor White
Write-Host "4. Test execution (10 min)" -ForegroundColor White
Write-Host ""
Write-Host "See RECOMMENDED_SETUP_GUIDE.md for details" -ForegroundColor Yellow
