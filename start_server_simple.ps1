# 統合APIサーバー起動スクリプト（シンプル版）

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "統合APIサーバーを起動します" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 作業ディレクトリに移動
Set-Location "C:\Users\mana4\Desktop\manaos_integrations"

# サーバーを起動
Write-Host "サーバーを起動中..." -ForegroundColor Yellow
Write-Host ""

# 新しいウィンドウでサーバーを起動（PORT=9502）
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\mana4\Desktop\manaos_integrations'; `$env:PORT='9502'; py -3.10 unified_api_server.py" -WorkingDirectory (Get-Location)

Write-Host "[OK] サーバーを起動しました" -ForegroundColor Green
Write-Host ""
Write-Host "サーバーが起動するまで10-30秒かかる場合があります" -ForegroundColor Yellow
Write-Host ""
Write-Host "確認方法:" -ForegroundColor Cyan
Write-Host "1. ブラウザで http://127.0.0.1:9502/health にアクセス" -ForegroundColor White
Write-Host "2. または、別のPowerShellウィンドウで以下を実行:" -ForegroundColor White
Write-Host "   python check_server_status.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
