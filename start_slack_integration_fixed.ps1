# Slack統合サーバー起動スクリプト（環境変数込み）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Slack統合サーバー起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 既存のプロセスを停止
Write-Host "`n[1/3] 既存のプロセスを停止中..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 5114 -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $processes) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $pid").CommandLine
            if ($cmdLine -like "*slack_integration*") {
                Write-Host "  プロセス $pid を停止中..." -ForegroundColor Cyan
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "  [OK] 停止完了" -ForegroundColor Green
}

# 2. 設定を読み込み（Secretsの直書き/ファイル走査はしない）
Write-Host "`n[2/3] 環境変数から認証情報を読み込み中..." -ForegroundColor Yellow
$webhookUrl = $env:SLACK_WEBHOOK_URL
$botToken = $env:SLACK_BOT_TOKEN
$verificationToken = $env:SLACK_VERIFICATION_TOKEN

# 環境変数を設定
$env:SLACK_WEBHOOK_URL = $webhookUrl
$env:SLACK_BOT_TOKEN = $botToken
$env:SLACK_VERIFICATION_TOKEN = $verificationToken
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"

Write-Host "  Webhook URL: $(if ($webhookUrl) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($webhookUrl) { 'Green' } else { 'Yellow' })
Write-Host "  Bot Token: $(if ($botToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($botToken) { 'Green' } else { 'Yellow' })
Write-Host "  Verification Token: $(if ($verificationToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($verificationToken) { 'Green' } else { 'Yellow' })

# 3. サーバーを起動
Write-Host "`n[3/3] サーバーを起動中..." -ForegroundColor Yellow
$scriptPath = Join-Path $PSScriptRoot "slack_integration.py"

if (Test-Path $scriptPath) {
    Start-Process python -ArgumentList $scriptPath -WindowStyle Normal
    Start-Sleep -Seconds 5
    
    # 起動確認
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:5114/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "  [OK] サーバーが正常に起動しました" -ForegroundColor Green
            
            # 設定確認
            $testResponse = Invoke-RestMethod -Uri "http://localhost:5114/api/slack/test" -Method Get -TimeoutSec 5 -ErrorAction Stop
            Write-Host "`n設定確認:" -ForegroundColor Cyan
            Write-Host "  Webhook URL: $(if ($testResponse.slack_webhook_configured) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($testResponse.slack_webhook_configured) { 'Green' } else { 'Yellow' })
            Write-Host "  Verification Token: $(if ($testResponse.slack_verification_token_configured) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($testResponse.slack_verification_token_configured) { 'Green' } else { 'Yellow' })
        }
    } catch {
        Write-Host "  [WARN] 起動確認に失敗しました" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] スクリプトが見つかりません: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
