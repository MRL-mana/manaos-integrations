# ローカルn8nサーバー用のAPIキーを設定するスクリプト

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     n8n APIキー設定（ローカルサーバー用）                        ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 設定ファイルのパス
$mcpConfigPath1 = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
$mcpConfigPath2 = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "[手順]" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ブラウザでn8nのWeb UIを開いてください:" -ForegroundColor White
Write-Host "   http://localhost:5679" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. ログイン後、APIキーを作成してください:" -ForegroundColor White
Write-Host "   Settings → API → Create API Key" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 作成したAPIキーをコピーしてください" -ForegroundColor White
Write-Host ""

# APIキーを入力
Write-Host "作成したAPIキーを入力してください:" -ForegroundColor Yellow
$apiKey = Read-Host "APIキー"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host ""
    Write-Host "❌ APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[設定ファイルを更新中...]" -ForegroundColor Yellow
Write-Host ""

$updated = $false

# 設定ファイル1を更新
if (Test-Path $mcpConfigPath1) {
    try {
        $config1 = Get-Content $mcpConfigPath1 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config1.mcpServers.n8n) {
            $config1.mcpServers.n8n.env.N8N_API_KEY = $apiKey
            $config1 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath1 -Encoding UTF8
            Write-Host "   ✅ cline_mcp_settings.json を更新しました" -ForegroundColor Green
            $updated = $true
        }
    } catch {
        Write-Host "   ❌ cline_mcp_settings.json の更新に失敗: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  cline_mcp_settings.json が見つかりません" -ForegroundColor Yellow
}

# 設定ファイル2を更新
if (Test-Path $mcpConfigPath2) {
    try {
        $config2 = Get-Content $mcpConfigPath2 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config2.mcpServers.n8n) {
            $config2.mcpServers.n8n.env.N8N_API_KEY = $apiKey
            $config2 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath2 -Encoding UTF8
            Write-Host "   ✅ mcp.json を更新しました" -ForegroundColor Green
            $updated = $true
        }
    } catch {
        Write-Host "   ❌ mcp.json の更新に失敗: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  mcp.json が見つかりません" -ForegroundColor Yellow
}

Write-Host ""

if ($updated) {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                                    ║" -ForegroundColor Green
    Write-Host "║     ✅ APIキーを設定しました！                                    ║" -ForegroundColor Green
    Write-Host "║                                                                    ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 次のステップ:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Cursorを再起動してMCP設定を反映してください" -ForegroundColor White
    Write-Host "2. n8n MCPサーバーが正常に動作するか確認してください" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "❌ 設定ファイルの更新に失敗しました" -ForegroundColor Red
    exit 1
}
