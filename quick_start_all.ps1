# ManaOS統合システム クイックスタートスクリプト
# すべてのサービスを起動して動作確認

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ManaOS統合システム クイックスタート" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. ComfyUI起動確認
Write-Host "[1] ComfyUI起動確認..." -ForegroundColor Yellow
$comfyuiProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*ComfyUI*" -or $_.CommandLine -like "*ComfyUI*"
}
if ($comfyuiProcess) {
    Write-Host "   [OK] ComfyUIは起動中です" -ForegroundColor Green
} else {
    Write-Host "   [NG] ComfyUIが起動していません" -ForegroundColor Red
    Write-Host "   起動しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Start-Process powershell -ArgumentList "-File", ".\start_comfyui_local.ps1" -WindowStyle Minimized
        Write-Host "   ComfyUIを起動しました" -ForegroundColor Green
        Start-Sleep -Seconds 5
    }
}
Write-Host ""

# 2. Google Drive認証確認
Write-Host "[2] Google Drive認証確認..." -ForegroundColor Yellow
$credentialsPath = Join-Path $scriptDir "credentials.json"
$tokenPath = Join-Path $scriptDir "token.json"
if ((Test-Path $credentialsPath) -and (Test-Path $tokenPath)) {
    Write-Host "   [OK] Google Drive認証情報が設定されています" -ForegroundColor Green
} else {
    Write-Host "   [NG] Google Drive認証情報が不足しています" -ForegroundColor Red
    Write-Host "   セットアップしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        .\setup_google_drive.ps1
    }
}
Write-Host ""

# 3. 統合APIサーバー起動
Write-Host "[3] 統合APIサーバー起動..." -ForegroundColor Yellow
$apiServerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*unified_api_server.py*"
}
if ($apiServerProcess) {
    Write-Host "   [OK] 統合APIサーバーは起動中です" -ForegroundColor Green
} else {
    Write-Host "   [INFO] 統合APIサーバーを起動します" -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:PORT='9502'; py -3.10 unified_api_server.py" -WindowStyle Normal
    Write-Host "   統合APIサーバーを起動しました（別ウィンドウ）" -ForegroundColor Green
    Write-Host "   数秒待ってからテストを実行してください" -ForegroundColor Gray
    Start-Sleep -Seconds 5
}
Write-Host ""

# 4. 動作確認
Write-Host "[4] 動作確認..." -ForegroundColor Yellow
Write-Host "   統合テストを実行しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    python complete_integration_test.py
} else {
    Write-Host "   スキップしました" -ForegroundColor Gray
}
Write-Host ""

# 5. n8nワークフロー確認
Write-Host "[5] n8nワークフロー確認..." -ForegroundColor Yellow
$n8nWebhookUrl = $env:N8N_WEBHOOK_URL
if ($n8nWebhookUrl) {
    Write-Host "   [OK] n8n Webhook URLが設定されています" -ForegroundColor Green
    Write-Host "   URL: $n8nWebhookUrl" -ForegroundColor Gray
} else {
    Write-Host "   [INFO] n8n Webhook URLが設定されていません" -ForegroundColor Yellow
    Write-Host "   設定する場合:" -ForegroundColor Cyan
    Write-Host "   `$env:N8N_WEBHOOK_URL = 'http://100.93.120.33:5678/webhook/comfyui-generated'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   n8nワークフローの作成:" -ForegroundColor Cyan
    Write-Host "   n8n_ワークフローセットアップ.md を参照" -ForegroundColor Gray
}
Write-Host ""

# まとめ
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "クイックスタート完了" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""
Write-Host "利用可能なエンドポイント:" -ForegroundColor Yellow
Write-Host "  POST http://127.0.0.1:9502/api/comfyui/generate - 画像生成" -ForegroundColor Gray
Write-Host "  GET  http://127.0.0.1:9502/api/civitai/search - モデル検索" -ForegroundColor Gray
Write-Host "  POST http://127.0.0.1:9502/api/google_drive/upload - ファイルアップロード" -ForegroundColor Gray
Write-Host ""
Write-Host "詳細:" -ForegroundColor Yellow
Write-Host "  FINAL_SETUP_GUIDE.md を参照" -ForegroundColor Gray
Write-Host ""


















