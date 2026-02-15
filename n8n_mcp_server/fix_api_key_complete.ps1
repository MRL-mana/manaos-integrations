# N8N APIキー完全修正スクリプト
# このスクリプトは、N8NのAPIキーを取得してMCP設定ファイルに設定します

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "N8N APIキー完全修正スクリプト" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 設定
$N8N_URL = "http://127.0.0.1:5679"
$MCP_CONFIG_PATH = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

# Step 1: N8Nの状態確認
Write-Host "[1/6] N8Nの状態を確認中..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-RestMethod -Uri "$N8N_URL/healthz" -Method Get -TimeoutSec 5
    if ($healthCheck.status -eq "ok") {
        Write-Host "[OK] N8Nは起動しています" -ForegroundColor Green
    } else {
        Write-Host "[NG] N8Nのヘルスチェックが失敗しました" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[NG] N8Nに接続できません: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "N8Nを起動してください:" -ForegroundColor Yellow
    Write-Host "  cd C:\Users\mana4\Desktop\manaos_integrations" -ForegroundColor Gray
    Write-Host "  .\start_n8n_local.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host ""

# Step 2: MCP設定ファイルの確認
Write-Host "[2/6] MCP設定ファイルを確認中..." -ForegroundColor Yellow
if (-not (Test-Path $MCP_CONFIG_PATH)) {
    Write-Host "[NG] MCP設定ファイルが見つかりません: $MCP_CONFIG_PATH" -ForegroundColor Red
    Write-Host "CursorのMCP設定を確認してください" -ForegroundColor Yellow
    exit 1
}

try {
    $config = Get-Content $MCP_CONFIG_PATH -Raw | ConvertFrom-Json
    if (-not $config.mcpServers.n8n) {
        Write-Host "[NG] n8n MCPサーバーの設定が見つかりません" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] MCP設定ファイルが見つかりました" -ForegroundColor Green
} catch {
    Write-Host "[NG] MCP設定ファイルの読み込みに失敗: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: N8NのWeb UIを開く
Write-Host "[3/6] N8NのWeb UIを開きます..." -ForegroundColor Yellow
Write-Host ""
Write-Host "以下の手順でAPIキーを作成してください:" -ForegroundColor Cyan
Write-Host "  1. ブラウザで開いたN8Nにログイン" -ForegroundColor White
Write-Host "  2. 右上のユーザーアイコンをクリック" -ForegroundColor White
Write-Host "  3. Settings を選択" -ForegroundColor White
Write-Host "  4. 左メニューから API を選択" -ForegroundColor White
Write-Host "  5. Create API Key をクリック" -ForegroundColor White
Write-Host "  6. APIキー名を入力（例: MCP Server）" -ForegroundColor White
Write-Host "  7. Create をクリック" -ForegroundColor White
Write-Host "  8. ⚠️ 表示されたAPIキーをコピー（重要！）" -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 2
Start-Process "$N8N_URL/settings/api"

Write-Host ""
Write-Host "APIキーをコピーしたら、Enterキーを押してください..." -ForegroundColor Yellow
Read-Host

Write-Host ""

# Step 4: APIキーの入力
Write-Host "[4/6] APIキーを入力してください..." -ForegroundColor Yellow
$apiKey = Read-Host "APIキー"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[NG] APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

# APIキーの形式確認（JWT形式かどうか）
if ($apiKey -notmatch "^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)$") {
    Write-Host "[警告] APIキーの形式が正しくない可能性があります" -ForegroundColor Yellow
    Write-Host "続行しますか？ (Y/N)" -ForegroundColor Yellow
    $confirm = Read-Host
    if ($confirm -ne "Y" -and $confirm -ne "y") {
        exit 1
    }
}

Write-Host "[OK] APIキーを受け取りました" -ForegroundColor Green
Write-Host ""

# Step 5: APIキーの動作確認
Write-Host "[5/6] APIキーの動作確認中..." -ForegroundColor Yellow
try {
    $headers = @{
        "X-N8N-API-KEY" = $apiKey
        "Content-Type" = "application/json"
    }
    
    $response = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows" -Method Get -Headers $headers -TimeoutSec 10
    
    Write-Host "[OK] APIキーは有効です！" -ForegroundColor Green
    if ($response -is [Array]) {
        Write-Host "  ワークフロー数: $($response.Count)" -ForegroundColor Gray
    } elseif ($response.data) {
        Write-Host "  ワークフロー数: $($response.data.Count)" -ForegroundColor Gray
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401) {
        Write-Host "[NG] APIキーが無効です（401 Unauthorized）" -ForegroundColor Red
        Write-Host ""
        Write-Host "確認事項:" -ForegroundColor Yellow
        Write-Host "  1. APIキーを正しくコピーしましたか？" -ForegroundColor White
        Write-Host "  2. N8NのWeb UIでAPIキーが作成されましたか？" -ForegroundColor White
        Write-Host "  3. ポート5679のN8Nインスタンスで作成しましたか？" -ForegroundColor White
        Write-Host ""
        Write-Host "もう一度やり直してください" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "[NG] APIキーの確認中にエラーが発生: $_" -ForegroundColor Red
        Write-Host "ステータスコード: $statusCode" -ForegroundColor Gray
        exit 1
    }
}

Write-Host ""

# Step 6: MCP設定ファイルを更新
Write-Host "[6/6] MCP設定ファイルを更新中..." -ForegroundColor Yellow

try {
    # 設定を更新
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    
    $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
    $config.mcpServers.n8n.env.N8N_BASE_URL = $N8N_URL
    
    # バックアップを作成
    $backupPath = "$MCP_CONFIG_PATH.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item $MCP_CONFIG_PATH $backupPath
    Write-Host "[OK] バックアップを作成しました: $backupPath" -ForegroundColor Gray
    
    # JSONに変換して保存
    $json = $config | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($MCP_CONFIG_PATH, $json, [System.Text.Encoding]::UTF8)
    
    Write-Host "[OK] MCP設定ファイルを更新しました" -ForegroundColor Green
    Write-Host "  ファイル: $MCP_CONFIG_PATH" -ForegroundColor Gray
    
} catch {
    Write-Host "[NG] MCP設定ファイルの更新に失敗: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "完了！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "  1. Cursorを完全に再起動してください" -ForegroundColor White
Write-Host "  2. CursorでMCPツールを試してください:" -ForegroundColor White
Write-Host "     n8n_list_workflows を使ってワークフロー一覧を取得" -ForegroundColor Gray
Write-Host ""
Write-Host "動作確認コマンド:" -ForegroundColor Yellow
Write-Host "  python n8n_mcp_server\test_mcp_connection.py" -ForegroundColor Gray
Write-Host ""
