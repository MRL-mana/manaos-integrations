# ngrok起動スクリプト（Slack Integration用・ポート5114）

Write-Host "=== ngrok トンネル起動（Slack Integration） ===" -ForegroundColor Cyan
Write-Host ""

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
Write-Host "ポート: 5114 (Slack Integration)" -ForegroundColor Gray
Write-Host ""

# ngrokを新しいウィンドウで起動
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd C:\Users\mana4\Desktop\ngrok; Write-Host '=== ngrok トンネル（Slack Integration） ===' -ForegroundColor Cyan; Write-Host ''; Write-Host 'ポート5114を公開中...' -ForegroundColor Yellow; Write-Host ''; Write-Host 'Web UI: http://127.0.0.1:4040' -ForegroundColor Green; Write-Host ''; Write-Host 'URLが表示されたら、以下の形式でSlack Appに設定してください:' -ForegroundColor White; Write-Host 'https://xxxx-xxxx-xxxx.ngrok-free.app/slack/events' -ForegroundColor Cyan; Write-Host ''; Write-Host '停止する場合は Ctrl+C を押してください' -ForegroundColor Gray; Write-Host ''; .\ngrok.exe http 5114"
)

Write-Host ""
Write-Host "✅ ngrokを起動しました" -ForegroundColor Green
Write-Host ""
Write-Host "新しいウィンドウでngrokが起動しています。" -ForegroundColor White
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. ngrokウィンドウで表示されたURLを確認" -ForegroundColor White
Write-Host "2. Slack Appの設定画面で、Request URLを更新:" -ForegroundColor White
Write-Host "   https://xxxx-xxxx-xxxx.ngrok-free.app/slack/events" -ForegroundColor Cyan
Write-Host "3. Slackでメッセージを送信してテスト" -ForegroundColor White
Write-Host ""
