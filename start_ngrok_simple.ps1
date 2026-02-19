# ngrok簡単起動スクリプト

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "=== ngrok トンネル起動 ===" -ForegroundColor Cyan
Write-Host ""

$ngrokBaseUrl = if ($env:NGROK_URL) { $env:NGROK_URL.TrimEnd('/') } else { "http://127.0.0.1:4040" }

# ngrokの場所
$ngrokPath = "C:\Users\mana4\Desktop\ngrok\ngrok.exe"

# ngrokが存在するか確認
if (-not (Test-Path $ngrokPath)) {
    Write-Host "❌ ngrok.exeが見つかりません: $ngrokPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "ngrokの場所を確認してください。" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ ngrok.exeが見つかりました" -ForegroundColor Green
Write-Host ""

# 既存のngrokプロセスを停止
$existingProcess = Get-Process ngrok -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "既存のngrokプロセスを停止します..." -ForegroundColor Yellow
    Stop-Process -Name ngrok -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "ngrokを起動します..." -ForegroundColor Green
Write-Host "ポート: 5678 (n8n)" -ForegroundColor Gray
Write-Host ""

# ngrokを新しいウィンドウで起動
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd C:\Users\mana4\Desktop\ngrok; Write-Host '=== ngrok トンネル ===' -ForegroundColor Cyan; Write-Host ''; Write-Host 'ポート5678を公開中...' -ForegroundColor Yellow; Write-Host ''; Write-Host 'Web UI: $ngrokBaseUrl' -ForegroundColor Green; Write-Host ''; Write-Host 'URLが表示されたら、以下の形式でBrowse AIに設定してください:' -ForegroundColor White; Write-Host 'https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook' -ForegroundColor Cyan; Write-Host ''; Write-Host '停止する場合は Ctrl+C を押してください' -ForegroundColor Gray; Write-Host ''; .\ngrok.exe http 5678"
)

Write-Host ""
Write-Host "✅ ngrokを起動しました" -ForegroundColor Green
Write-Host ""
Write-Host "新しいウィンドウでngrokが起動しています。" -ForegroundColor White
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. ngrokウィンドウでURLを確認" -ForegroundColor White
Write-Host "2. Web UIで確認: $ngrokBaseUrl" -ForegroundColor White
Write-Host "3. Browse AIに設定: https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook" -ForegroundColor White
Write-Host ""


