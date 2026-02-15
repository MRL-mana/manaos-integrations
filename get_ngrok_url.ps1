# ngrok URL取得スクリプト

Write-Host "=== ngrok URL取得 ===" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -Method Get -TimeoutSec 10

    if ($response.tunnels -and $response.tunnels.Count -gt 0) {
        $publicUrl = $response.tunnels[0].public_url
        $slackUrl = "$publicUrl/api/slack/events"

        Write-Host "`nngrok URL: $publicUrl" -ForegroundColor Green
        Write-Host "`nSlack Events API URL:" -ForegroundColor Yellow
        Write-Host "$slackUrl" -ForegroundColor Cyan

        # クリップボードにコピー
        $slackUrl | Set-Clipboard
        Write-Host "`n✅ クリップボードにコピーしました！" -ForegroundColor Green
        Write-Host "`nこのURLをSlack AppのEvent Subscriptionsに設定してください" -ForegroundColor White
    } else {
        Write-Host "`n⚠️ ngrokは起動していますが、トンネルがまだ作成されていません" -ForegroundColor Yellow
        Write-Host "もう少し待ってから再度実行してください" -ForegroundColor White
    }
} catch {
    Write-Host "`n❌ ngrokのWeb UIに接続できません" -ForegroundColor Red
    Write-Host "`n確認方法:" -ForegroundColor Yellow
    Write-Host "1. ngrokが起動しているか確認" -ForegroundColor White
    Write-Host "2. ngrokのターミナルウィンドウでURLを確認" -ForegroundColor White
    Write-Host "3. http://127.0.0.1:4040 にブラウザでアクセス" -ForegroundColor White
}
