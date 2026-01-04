# n8nワークフローを再アクティベートするクイックスクリプト
# Web UIから手動で実行する方法も案内

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "n8nワークフロー再アクティベート" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

Write-Host "方法1: Web UIから手動実行（推奨）" -ForegroundColor Yellow
Write-Host "1. ブラウザで http://localhost:5679 を開く" -ForegroundColor White
Write-Host "2. ワークフロー一覧で「ManaOS Image Generation Workflow」を開く" -ForegroundColor White
Write-Host "3. 右上のトグルスイッチを一度OFFにする" -ForegroundColor White
Write-Host "4. 2-3秒待つ" -ForegroundColor White
Write-Host "5. 再度ONにする" -ForegroundColor White
Write-Host "6. これでWebhookが再登録されます" -ForegroundColor White
Write-Host ""

Write-Host "方法2: API経由で実行" -ForegroundColor Yellow
Write-Host "まず、新しいAPIキーを取得してください:" -ForegroundColor White
Write-Host "1. http://localhost:5679 を開く" -ForegroundColor White
Write-Host "2. 右上のユーザーアイコン → Settings → API" -ForegroundColor White
Write-Host "3. 「Create API Key」をクリック" -ForegroundColor White
Write-Host "4. 生成されたAPIキーをコピー" -ForegroundColor White
Write-Host "5. 以下のコマンドで設定:" -ForegroundColor White
Write-Host '   $env:N8N_API_KEY = "YOUR_API_KEY_HERE"' -ForegroundColor Green
Write-Host ""

Write-Host "APIキーを設定したら、以下を実行:" -ForegroundColor Yellow
Write-Host '   python n8n_mcp_server/reactivate_workflow.py 2ViGYzDtLBF6H4zn' -ForegroundColor Green
Write-Host ""

Write-Host "現在のAPIキーを確認:" -ForegroundColor Yellow
$apiKey = $env:N8N_API_KEY
if ($apiKey) {
    Write-Host "   APIキーが設定されています: $($apiKey.Substring(0, 20))..." -ForegroundColor Green
} else {
    Write-Host "   APIキーが設定されていません" -ForegroundColor Red
}
Write-Host ""












