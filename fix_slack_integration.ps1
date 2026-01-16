# Slack統合の修復スクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Slack統合の修復" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 環境変数から認証情報を読み込み（Secretsの直書き/ファイル走査はしない）
Write-Host "`n[1/5] 環境変数から認証情報を読み込み中..." -ForegroundColor Yellow
$webhookUrl = $env:SLACK_WEBHOOK_URL
$botToken = $env:SLACK_BOT_TOKEN
$verificationToken = $env:SLACK_VERIFICATION_TOKEN

Write-Host "  Webhook URL: $(if ($webhookUrl) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($webhookUrl) { 'Green' } else { 'Yellow' })
Write-Host "  Bot Token: $(if ($botToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($botToken) { 'Green' } else { 'Yellow' })
Write-Host "  Verification Token: $(if ($verificationToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($verificationToken) { 'Green' } else { 'Yellow' })

# 3. 環境変数を設定
Write-Host "`n[3/5] 環境変数を設定中..." -ForegroundColor Yellow

if ($webhookUrl) {
    $env:SLACK_WEBHOOK_URL = $webhookUrl
    Write-Host "  [OK] SLACK_WEBHOOK_URL: 設定済み" -ForegroundColor Green
} else {
    Write-Host "  [WARN] SLACK_WEBHOOK_URL: 未設定" -ForegroundColor Yellow
}

if ($botToken) {
    $env:SLACK_BOT_TOKEN = $botToken
    Write-Host "  [OK] SLACK_BOT_TOKEN: 設定済み" -ForegroundColor Green
} else {
    Write-Host "  [WARN] SLACK_BOT_TOKEN: 未設定" -ForegroundColor Yellow
}

if ($verificationToken) {
    $env:SLACK_VERIFICATION_TOKEN = $verificationToken
    Write-Host "  [OK] SLACK_VERIFICATION_TOKEN: 設定済み" -ForegroundColor Green
} else {
    Write-Host "  [WARN] SLACK_VERIFICATION_TOKEN: 未設定" -ForegroundColor Yellow
}

# その他の必要な環境変数
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"

# 4. 既存のSlack統合サーバーを停止
Write-Host "`n[4/5] 既存のSlack統合サーバーを停止中..." -ForegroundColor Yellow

# ポート5114を使用しているプロセスを確認
$port = 5114
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $processes) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $pid").CommandLine
            if ($cmdLine -like "*slack_integration*") {
                Write-Host "  [INFO] プロセス $pid を停止中..." -ForegroundColor Cyan
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "  [OK] 既存のプロセスを停止しました" -ForegroundColor Green
} else {
    Write-Host "  [INFO] 実行中のプロセスは見つかりませんでした" -ForegroundColor Cyan
}

# 5. Slack統合サーバーを起動
Write-Host "`n[5/5] Slack統合サーバーを起動中..." -ForegroundColor Yellow

$scriptPath = Join-Path $PSScriptRoot "slack_integration.py"
if (Test-Path $scriptPath) {
    # バックグラウンドで起動
    $process = Start-Process python -ArgumentList $scriptPath -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 3
    
    # 起動確認
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:5114/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "  [OK] Slack統合サーバーが正常に起動しました" -ForegroundColor Green
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

# 6. テスト
Write-Host "`n[6/6] 接続テスト中..." -ForegroundColor Yellow
try {
    $testResponse = Invoke-RestMethod -Uri "http://localhost:5114/api/slack/test" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  [OK] 接続テスト成功" -ForegroundColor Green
    Write-Host "  Orchestrator URL: $($testResponse.orchestrator_url)" -ForegroundColor Cyan
    Write-Host "  Webhook URL設定: $($testResponse.slack_webhook_configured)" -ForegroundColor Cyan
    Write-Host "  Verification Token設定: $($testResponse.slack_verification_token_configured)" -ForegroundColor Cyan
} catch {
    Write-Host "  [WARN] 接続テストに失敗しました: $_" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "修復完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n設定された環境変数:" -ForegroundColor Yellow
Write-Host "  SLACK_WEBHOOK_URL: $(if ($webhookUrl) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($webhookUrl) { 'Green' } else { 'Yellow' })
Write-Host "  SLACK_BOT_TOKEN: $(if ($botToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($botToken) { 'Green' } else { 'Yellow' })
Write-Host "  SLACK_VERIFICATION_TOKEN: $(if ($verificationToken) { '設定済み' } else { '未設定' })" -ForegroundColor $(if ($verificationToken) { 'Green' } else { 'Yellow' })

Write-Host "`n注意: 環境変数は現在のセッションでのみ有効です" -ForegroundColor Gray
Write-Host "永続的に設定する場合は、システム環境変数に設定するか、.envファイルを使用してください" -ForegroundColor Gray
