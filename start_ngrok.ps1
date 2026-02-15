#!/usr/bin/env pwsh
# ngrok起動スクリプト（ポート5114）

Write-Host "ngrokを起動します（ポート5114）..." -ForegroundColor Yellow

# 既存のngrokプロセスを停止
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# ngrokを起動
try {
    # バックグラウンドでngrokを起動
    $ngrokProcess = Start-Process ngrok -ArgumentList "http", "5114" -PassThru -WindowStyle Normal -ErrorAction Stop
    Write-Host "✅ ngrok起動成功（PID: $($ngrokProcess.Id)）" -ForegroundColor Green
    Write-Host "`n数秒待ってから、以下のURLを確認してください:" -ForegroundColor Cyan
    Write-Host "  http://127.0.0.1:4040" -ForegroundColor White
    Write-Host "`nまたは、以下のコマンドでURLを取得:" -ForegroundColor Cyan
    Write-Host "  Invoke-RestMethod http://127.0.0.1:4040/api/tunnels | ConvertTo-Json" -ForegroundColor White
} catch {
    Write-Host "❌ ngrok起動失敗: $_" -ForegroundColor Red
    Write-Host "`n手動でngrokを起動してください:" -ForegroundColor Yellow
    Write-Host "  新しいPowerShellウィンドウで: ngrok http 5114" -ForegroundColor White
}
