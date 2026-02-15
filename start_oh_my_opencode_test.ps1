# OH MY OPENCODE統合テスト起動スクリプト

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "OH MY OPENCODE統合テスト" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 環境変数の確認
$apiKey = [System.Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY', 'User')
if ($apiKey) {
    Write-Host "[OK] OpenRouter APIキーが設定されています" -ForegroundColor Green
    Write-Host ("   キー: " + $apiKey.Substring(0, [Math]::Min(20, $apiKey.Length)) + "...") -ForegroundColor Gray
} else {
    Write-Host "[NG] OpenRouter APIキーが設定されていません" -ForegroundColor Red
    Write-Host "    設定スクリプトを実行してください: python set_openrouter_api_key.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "統合APIサーバーを起動します..." -ForegroundColor Yellow
Write-Host ""

# 統合APIサーバーをバックグラウンドで起動（PORT=9510）
$serverProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; `$env:PYTHONIOENCODING='utf-8'; `$env:PORT='9510'; py -3.10 unified_api_server.py" -PassThru -WindowStyle Minimized

Write-Host "[OK] 統合APIサーバーを起動しました (PID: $($serverProcess.Id))" -ForegroundColor Green
Write-Host ""

# サーバーが起動するまで待機
Write-Host "サーバーの起動を待機中..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# ヘルスチェック
Write-Host ""
Write-Host "ヘルスチェックを実行中..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:9510/health" -TimeoutSec 5 | Out-Null
    if ($true) {
        Write-Host "[OK] サーバーが正常に起動しました" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] サーバーの起動確認に失敗しました" -ForegroundColor Yellow
    Write-Host "      数秒待ってから再度確認してください" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. 別のPowerShellウィンドウで以下を実行:" -ForegroundColor White
Write-Host "   python test_oh_my_opencode_integration.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. または、ブラウザで以下にアクセス:" -ForegroundColor White
Write-Host "   http://127.0.0.1:9510/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. サーバーを停止する場合:" -ForegroundColor White
Write-Host "   Stop-Process -Id $($serverProcess.Id)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
