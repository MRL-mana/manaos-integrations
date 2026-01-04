# ngrok authtoken取得・設定ガイドスクリプト

Write-Host "=== ngrok authtoken設定ガイド ===" -ForegroundColor Cyan
Write-Host ""

# ブラウザでngrokダッシュボードを開く
Write-Host "ngrokダッシュボードを開きます..." -ForegroundColor Green
Start-Process "https://dashboard.ngrok.com/get-started/your-authtoken"

Write-Host ""
Write-Host "=== 手順 ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ngrokダッシュボードでログイン（またはアカウント作成）" -ForegroundColor White
Write-Host ""
Write-Host "2. 「Your Authtoken」セクションを確認" -ForegroundColor White
Write-Host "   - 1つの長い文字列（約40文字以上）" -ForegroundColor Gray
Write-Host "   - ハイフンで区切られていない" -ForegroundColor Gray
Write-Host "   - 英数字のみ" -ForegroundColor Gray
Write-Host ""
Write-Host "3. authtokenをコピー" -ForegroundColor White
Write-Host ""
Write-Host "4. 以下のコマンドを実行して設定:" -ForegroundColor White
Write-Host ""
Write-Host "   cd C:\Users\mana4\Desktop\ngrok" -ForegroundColor Cyan
Write-Host "   .\ngrok.exe config add-authtoken YOUR_AUTHTOKEN_HERE" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. 設定後、ngrokを起動:" -ForegroundColor White
Write-Host ""
Write-Host "   .\ngrok.exe http 5678" -ForegroundColor Cyan
Write-Host ""

# 現在の設定ファイルを確認
$configPath = "$env:LOCALAPPDATA\ngrok\ngrok.yml"
if (Test-Path $configPath) {
    Write-Host "=== 現在の設定ファイル ===" -ForegroundColor Yellow
    Write-Host ""
    $config = Get-Content $configPath
    # authtokenの部分だけをマスクして表示
    $maskedConfig = $config | ForEach-Object {
        if ($_ -match "authtoken:\s*(.+)") {
            $token = $matches[1]
            $maskedToken = $token.Substring(0, [Math]::Min(10, $token.Length)) + "..." + $token.Substring([Math]::Max(0, $token.Length - 10))
            $_ -replace $token, $maskedToken
        } else {
            $_
        }
    }
    Write-Host ($maskedConfig -join "`n") -ForegroundColor Gray
    Write-Host ""
}

Write-Host "authtokenを取得したら、設定コマンドを実行してください。" -ForegroundColor Green
Write-Host ""


