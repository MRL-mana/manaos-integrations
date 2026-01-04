# n8nワークフローをこのはサーバー経由でインポート
# 注意: n8nのデータベース形式に合わせる必要がある場合があります

$WORKFLOW_FILE = "C:\Users\mana4\Desktop\manaos_integrations\n8n_workflow_template.json"
$KONOHA_SERVER = "100.93.120.33"
$N8N_WORKFLOWS_DIR = "/root/.n8n/workflows"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "n8nワークフロー インポート（SSH経由）" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ワークフローファイルの存在確認
if (-not (Test-Path $WORKFLOW_FILE)) {
    Write-Host "[NG] ワークフローファイルが見つかりません: $WORKFLOW_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] ワークフローファイルを確認: $WORKFLOW_FILE" -ForegroundColor Green

# このはサーバーに接続してワークフローをインポート
Write-Host "[OK] このはサーバーに接続中..." -ForegroundColor Green

# 方法1: n8nのREST API経由でインポート（推奨）
Write-Host ""
Write-Host "方法1: n8nのREST API経由でインポート" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$workflowJson = Get-Content $WORKFLOW_FILE -Raw -Encoding UTF8

# n8nのAPIエンドポイントに直接POST
$apiUrl = "http://${KONOHA_SERVER}:5678/api/v1/workflows"

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method POST -Body $workflowJson -ContentType "application/json" -TimeoutSec 30 -ErrorAction Stop
    
    Write-Host "[OK] ワークフローをインポートしました" -ForegroundColor Green
    Write-Host "  - ID: $($response.id)" -ForegroundColor Cyan
    Write-Host "  - 名前: $($response.name)" -ForegroundColor Cyan
    Write-Host "  - URL: http://${KONOHA_SERVER}:5678/workflow/$($response.id)" -ForegroundColor Cyan
    
    # ワークフローを有効化
    Write-Host ""
    Write-Host "[OK] ワークフローを有効化中..." -ForegroundColor Green
    
    $activateUrl = "http://${KONOHA_SERVER}:5678/api/v1/workflows/$($response.id)/activate"
    try {
        $activateResponse = Invoke-RestMethod -Uri $activateUrl -Method POST -TimeoutSec 30 -ErrorAction Stop
        Write-Host "[OK] ワークフローを有効化しました" -ForegroundColor Green
    } catch {
        Write-Host "[警告] ワークフローの有効化に失敗しました（手動で有効化してください）" -ForegroundColor Yellow
        Write-Host "  エラー: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "インポート完了" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[次のステップ]" -ForegroundColor Yellow
    Write-Host "1. n8nのWeb UIでワークフローを確認" -ForegroundColor White
    Write-Host "   URL: http://${KONOHA_SERVER}:5678" -ForegroundColor Cyan
    Write-Host "2. 必要に応じて認証情報を設定（Google Drive、Obsidian、Slack）" -ForegroundColor White
    Write-Host "3. 環境変数にWebhook URLを設定" -ForegroundColor White
    Write-Host "   `$env:N8N_WEBHOOK_URL = 'http://${KONOHA_SERVER}:5678/webhook/comfyui-generated'" -ForegroundColor Cyan
    Write-Host ""
    
    exit 0
    
} catch {
    Write-Host "[NG] API経由でのインポートに失敗しました" -ForegroundColor Red
    Write-Host "  エラー: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host ""
        Write-Host "[ヒント] n8nの認証が必要な可能性があります" -ForegroundColor Yellow
        Write-Host "  1. n8nのWeb UIにログイン" -ForegroundColor White
        Write-Host "  2. Settings → API → API Keyを作成" -ForegroundColor White
        Write-Host "  3. 環境変数 N8N_API_KEY に設定" -ForegroundColor White
        Write-Host ""
    }
    
    Write-Host ""
    Write-Host "方法2: ブラウザで手動インポート" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "1. n8nのWeb UIにアクセス" -ForegroundColor White
    Write-Host "   URL: http://${KONOHA_SERVER}:5678" -ForegroundColor Cyan
    Write-Host "2. 「Workflows」→「Import from File」をクリック" -ForegroundColor White
    Write-Host "3. ファイルを選択: $WORKFLOW_FILE" -ForegroundColor White
    Write-Host "4. 「Import」をクリック" -ForegroundColor White
    Write-Host ""
    
    exit 1
}


















