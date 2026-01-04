# ngrokセットアップスクリプト

Write-Host "ngrokセットアップ開始" -ForegroundColor Green
Write-Host ""

# ngrokのダウンロードURL
$ngrokUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$downloadPath = "$env:USERPROFILE\Downloads\ngrok.zip"
$extractPath = "$env:USERPROFILE\Desktop\ngrok"

Write-Host "Step 1: ngrokをダウンロード中..." -ForegroundColor Cyan
Write-Host "URL: $ngrokUrl" -ForegroundColor Gray
Write-Host "保存先: $downloadPath" -ForegroundColor Gray
Write-Host ""

try {
    # ngrokをダウンロード
    Invoke-WebRequest -Uri $ngrokUrl -OutFile $downloadPath -UseBasicParsing
    Write-Host "✅ ダウンロード完了" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ ダウンロードエラー: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "手動でダウンロードしてください:" -ForegroundColor Yellow
    Write-Host "1. https://ngrok.com/download にアクセス" -ForegroundColor White
    Write-Host "2. Windows版をダウンロード" -ForegroundColor White
    Write-Host "3. ZIPファイルを解凍" -ForegroundColor White
    exit 1
}

Write-Host "Step 2: ngrokを解凍中..." -ForegroundColor Cyan
Write-Host "解凍先: $extractPath" -ForegroundColor Gray
Write-Host ""

try {
    # フォルダを作成
    if (-not (Test-Path $extractPath)) {
        New-Item -ItemType Directory -Path $extractPath | Out-Null
    }
    
    # ZIPファイルを解凍
    Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force
    Write-Host "✅ 解凍完了" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ 解凍エラー: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "手動で解凍してください:" -ForegroundColor Yellow
    Write-Host "1. $downloadPath を開く" -ForegroundColor White
    Write-Host "2. ZIPファイルを右クリック → すべて展開" -ForegroundColor White
    exit 1
}

Write-Host "Step 3: ngrokの場所を確認..." -ForegroundColor Cyan
$ngrokExe = Get-ChildItem -Path $extractPath -Filter "ngrok.exe" -Recurse | Select-Object -First 1

if ($ngrokExe) {
    Write-Host "✅ ngrok.exeが見つかりました" -ForegroundColor Green
    Write-Host "場所: $($ngrokExe.FullName)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Step 4: ngrokをテスト実行..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "ngrokの使い方:" -ForegroundColor Yellow
    Write-Host "1. PowerShellで以下を実行:" -ForegroundColor White
    Write-Host "   cd '$($ngrokExe.DirectoryName)'" -ForegroundColor Gray
    Write-Host "   .\ngrok.exe http 5678" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. 出力されたURLをコピー:" -ForegroundColor White
    Write-Host "   https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Browse AIに設定:" -ForegroundColor White
    Write-Host "   - Browse AIダッシュボード → 統合する → Webhooks" -ForegroundColor Gray
    Write-Host "   - Webhook URLに上記のURLを入力" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ ngrok.exeが見つかりませんでした" -ForegroundColor Red
    Write-Host ""
    Write-Host "手動で確認してください:" -ForegroundColor Yellow
    Write-Host "1. $extractPath を開く" -ForegroundColor White
    Write-Host "2. ngrok.exeがあるか確認" -ForegroundColor White
}

Write-Host "セットアップ完了！" -ForegroundColor Green


