# n8nの実行履歴を確認するスクリプト

Write-Host "🔍 n8nの実行履歴を確認中..." -ForegroundColor Yellow
Write-Host ""

# n8nのAPIエンドポイント（ローカル）
$n8nUrl = "http://localhost:5678"

try {
    Write-Host "n8nに接続中..." -ForegroundColor Cyan
    
    # n8nのヘルスチェック
    $healthCheck = Invoke-RestMethod -Uri "$n8nUrl/healthz" -Method Get -ErrorAction Stop
    Write-Host "✅ n8nは起動しています" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "📋 確認手順:" -ForegroundColor Yellow
    Write-Host "1. ブラウザで http://localhost:5678 を開く" -ForegroundColor White
    Write-Host "2. 左メニューから「Executions」をクリック" -ForegroundColor White
    Write-Host "3. 最新の実行を確認:" -ForegroundColor White
    Write-Host "   - Browse AI Webhookノードでデータを受信しているか" -ForegroundColor White
    Write-Host "   - エラーが発生していないか" -ForegroundColor White
    Write-Host "   - 各ノードの出力データを確認" -ForegroundColor White
    Write-Host ""
    Write-Host "4. ワークフローを開いて確認:" -ForegroundColor White
    Write-Host "   - 右上のトグルスイッチがONになっているか" -ForegroundColor White
    Write-Host "   - 「データ整形・重要度判定」ノードの出力を確認" -ForegroundColor White
    Write-Host "     - importanceの値が5以上か" -ForegroundColor White
    Write-Host "     - shouldNotifyがtrueか" -ForegroundColor White
    Write-Host "   - 「Slack通知」ノードでエラーが発生していないか" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ n8nに接続できません" -ForegroundColor Red
    Write-Host "エラー: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "n8nが起動しているか確認してください:" -ForegroundColor Yellow
    Write-Host "  http://localhost:5678" -ForegroundColor White
    Write-Host ""
}

Write-Host "💡 ヒント:" -ForegroundColor Yellow
Write-Host "- 実行履歴に新しい実行がない場合、Browse AIからWebhookが呼ばれていません" -ForegroundColor White
Write-Host "- エラーが発生している場合、エラーメッセージを確認してください" -ForegroundColor White
Write-Host "- 重要度スコアが5未満の場合、通知判定でfalseになります" -ForegroundColor White
Write-Host ""

