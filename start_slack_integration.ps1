# Slack Integration起動スクリプト

Write-Host "=== Slack Integration起動 ===" -ForegroundColor Cyan

# 設定ファイルからWebhook URLを読み込み
$configPath = "notification_hub_enhanced_config.json"
if (Test-Path $configPath) {
    $config = Get-Content $configPath | ConvertFrom-Json
    $webhookUrl = $config.slack_webhook_url
    Write-Host "`n[1] 設定ファイルからWebhook URLを読み込みました" -ForegroundColor Green
    Write-Host "  Webhook URL: $webhookUrl" -ForegroundColor Gray
} else {
    Write-Host "`n[WARN] 設定ファイルが見つかりません: $configPath" -ForegroundColor Yellow
    $webhookUrl = ""
}

# 環境変数を設定
Write-Host "`n[2] 環境変数を設定中..." -ForegroundColor Yellow
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"

if ($webhookUrl) {
    $env:SLACK_WEBHOOK_URL = $webhookUrl
    Write-Host "  SLACK_WEBHOOK_URL: 設定済み" -ForegroundColor Green
} else {
    Write-Host "  SLACK_WEBHOOK_URL: 未設定（オプション）" -ForegroundColor Yellow
}

# 既存のプロセスを確認
Write-Host "`n[3] 既存のプロセスを確認中..." -ForegroundColor Yellow
$existingProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*slack_integration.py*"
}

if ($existingProcess) {
    Write-Host "  [INFO] 既存のプロセスが見つかりました（ID: $($existingProcess.Id)）" -ForegroundColor Cyan
    Write-Host "  停止して再起動しますか？ (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Stop-Process -Id $existingProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "  [OK] 既存のプロセスを停止しました" -ForegroundColor Green
    }
}

# Slack Integrationを起動
Write-Host "`n[4] Slack Integrationを起動中..." -ForegroundColor Yellow
$scriptPath = Join-Path $PSScriptRoot "slack_integration.py"

if (Test-Path $scriptPath) {
    Start-Process python -ArgumentList $scriptPath -WindowStyle Normal
    Start-Sleep -Seconds 3
    
    # 起動確認
    Write-Host "`n[5] 起動確認中..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:5114/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "  [OK] Slack Integrationが正常に起動しました" -ForegroundColor Green
            Write-Host "  URL: http://localhost:5114" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "  [WARN] 起動確認に失敗しました（起動中かもしれません）" -ForegroundColor Yellow
        Write-Host "  数秒後に再度確認してください: curl http://localhost:5114/health" -ForegroundColor Cyan
    }
} else {
    Write-Host "  [ERROR] スクリプトが見つかりません: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 完了 ===" -ForegroundColor Cyan
Write-Host "`n使用方法:" -ForegroundColor Yellow
Write-Host "  Slack Events API: http://localhost:5114/api/slack/events" -ForegroundColor White
Write-Host "  ヘルスチェック: http://localhost:5114/health" -ForegroundColor White
Write-Host "`n停止方法:" -ForegroundColor Yellow
Write-Host "  Get-Process python | Where-Object {`$_.CommandLine -like '*slack_integration.py*' } | Stop-Process" -ForegroundColor White

