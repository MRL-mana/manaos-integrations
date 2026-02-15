# n8nライセンスキーをアクティベートするスクリプト

$licenseKey = "b01a8246-6a35-4221-917e-b5b25028a21b"
$n8nUrl = "http://127.0.0.1:5679"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     n8nライセンスキーアクティベート                              ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] n8nサーバーの確認..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$n8nUrl/healthz" -Method GET -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ n8nサーバーは起動しています" -ForegroundColor Green
} catch {
    Write-Host "   ❌ n8nサーバーに接続できません" -ForegroundColor Red
    Write-Host "   → まずn8nサーバーを起動してください: .\start_n8n_local.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2] ブラウザでn8nのWeb UIを開きます..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:5679/settings/license"

Write-Host ""
Write-Host "   ✅ ブラウザを開きました" -ForegroundColor Green
Write-Host ""
Write-Host "[3] ライセンスキーをクリップボードにコピーします..." -ForegroundColor Yellow
$licenseKey | Set-Clipboard
Write-Host "   ✅ ライセンスキーをクリップボードにコピーしました" -ForegroundColor Green
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "║     📋 次のステップ                                                ║" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "1. ブラウザで開いたn8nのページで:" -ForegroundColor White
Write-Host "   • 「Enter activation key」をクリック" -ForegroundColor Gray
Write-Host "   • ライセンスキー欄に貼り付け（Ctrl+V）" -ForegroundColor Gray
Write-Host "   • 「Activate」をクリック" -ForegroundColor Gray
Write-Host ""
Write-Host "2. アクティベートが完了したら、このスクリプトを再実行して確認できます" -ForegroundColor White
Write-Host ""
Write-Host "ライセンスキー: $licenseKey" -ForegroundColor Cyan
Write-Host "（クリップボードにコピー済み）" -ForegroundColor Gray
Write-Host ""
