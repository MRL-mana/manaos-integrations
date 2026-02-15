# Browse AI統合自動セットアップスクリプト
# できる範囲で自動化

Write-Host "🚀 Browse AI統合自動セットアップ開始" -ForegroundColor Green
Write-Host ""

# Step 1: n8n確認
Write-Host "📋 Step 1: n8n確認中..." -ForegroundColor Yellow
$n8nPort = Test-NetConnection -ComputerName 127.0.0.1 -Port 5678 -InformationLevel Quiet
$portalPort = Test-NetConnection -ComputerName 127.0.0.1 -Port 5000 -InformationLevel Quiet

if ($n8nPort) {
    Write-Host "✅ n8nは起動しています (ポート5678)" -ForegroundColor Green
} else {
    Write-Host "❌ n8nが起動していません" -ForegroundColor Red
    Write-Host "   n8nを起動してください" -ForegroundColor Yellow
    exit 1
}

if ($portalPort) {
    Write-Host "✅ Portal UIは起動しています (ポート5000)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Portal UIが起動していません" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: ワークフローファイル確認
Write-Host "📋 Step 2: ワークフローファイル確認中..." -ForegroundColor Yellow
$workflowPath = Join-Path $PSScriptRoot "n8n_workflows\browse_ai_manaos_integration.json"
if (Test-Path $workflowPath) {
    Write-Host "✅ ワークフローファイルが見つかりました" -ForegroundColor Green
    Write-Host "   パス: $workflowPath" -ForegroundColor Cyan
    
    # ワークフローファイルの内容を読み込む
    $workflowContent = Get-Content $workflowPath -Raw
    $workflowJson = $workflowContent | ConvertFrom-Json
    
    Write-Host "   ワークフロー名: $($workflowJson.name)" -ForegroundColor Cyan
    Write-Host "   ノード数: $($workflowJson.nodes.Count)" -ForegroundColor Cyan
} else {
    Write-Host "❌ ワークフローファイルが見つかりません" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: ワークフローインポート準備
Write-Host "📋 Step 3: ワークフローインポート準備..." -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ 準備完了！次の手順でインポートしてください:" -ForegroundColor Green
Write-Host ""
Write-Host "【方法A: Portal UI経由（推奨・簡単）】" -ForegroundColor Cyan
Write-Host "1. ブラウザで開く: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "2. 「⚙️ 自動化ワークフロー（n8n）」セクションを開く" -ForegroundColor White
Write-Host "3. 「ワークフローをインポート」をクリック" -ForegroundColor White
Write-Host "4. ファイルを選択: $workflowPath" -ForegroundColor White
Write-Host ""
Write-Host "【方法B: n8n直接アクセス】" -ForegroundColor Cyan
Write-Host "1. ブラウザで開く: http://127.0.0.1:5678" -ForegroundColor White
Write-Host "2. ログイン（必要に応じて）" -ForegroundColor White
Write-Host "3. 「Workflows」→「Import from File」" -ForegroundColor White
Write-Host "4. ファイルを選択: $workflowPath" -ForegroundColor White
Write-Host ""

# Step 4: 次のステップ
Write-Host "📋 Step 4: 次のステップ..." -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ ワークフローインポート後:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Webhook URL確認:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:5678/webhook/browse-ai-webhook" -ForegroundColor White
Write-Host ""
Write-Host "2. Browse AIアカウント作成（手動）:" -ForegroundColor Cyan
Write-Host "   https://www.browse.ai/" -ForegroundColor White
Write-Host "   Starterプラン（`$49/月）" -ForegroundColor White
Write-Host ""
Write-Host "3. Slack Webhook URL取得（手動）:" -ForegroundColor Cyan
Write-Host "   https://api.slack.com/apps" -ForegroundColor White
Write-Host "   Incoming Webhooks有効化" -ForegroundColor White
Write-Host ""
Write-Host "4. Browse AI設定（手動）:" -ForegroundColor Cyan
Write-Host "   - ロボット作成: 'CivitAI Sale Monitor'" -ForegroundColor White
Write-Host "   - URL: https://civitai.com/models?onSale=true" -ForegroundColor White
Write-Host "   - Webhook設定: 上記のWebhook URL" -ForegroundColor White
Write-Host ""

# Step 5: クイックスタートガイド表示
Write-Host "📋 Step 5: 詳細ガイド..." -ForegroundColor Yellow
Write-Host ""
Write-Host "詳細は以下のファイルを参照してください:" -ForegroundColor Cyan
Write-Host "  - QUICK_START_BROWSE_AI.md (10分ガイド)" -ForegroundColor White
Write-Host "  - NEXT_STEPS.md (次のステップ)" -ForegroundColor White
Write-Host "  - RECOMMENDED_SETUP_GUIDE.md (詳細ガイド)" -ForegroundColor White
Write-Host ""

Write-Host "Setup preparation complete!" -ForegroundColor Green
Write-Host ""

