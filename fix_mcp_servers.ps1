# llm-routingとn8nのMCPサーバーを修正するスクリプト

Write-Host "=" * 60
Write-Host "MCPサーバーの修正スクリプト"
Write-Host "=" * 60
Write-Host ""

$mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

Write-Host "[1] 設定ファイルの確認..." -ForegroundColor Yellow

# 設定ファイルが存在しない場合は作成
if (-not (Test-Path $mcpConfigPath)) {
    Write-Host "   設定ファイルが存在しません。作成します..." -ForegroundColor Gray
    $configDir = Split-Path -Parent $mcpConfigPath
    if (-not (Test-Path $configDir)) {
        New-Item -Path $configDir -ItemType Directory -Force | Out-Null
    }
    $defaultConfig = @{
        mcpServers = @{}
    } | ConvertTo-Json -Depth 10
    Set-Content -Path $mcpConfigPath -Value $defaultConfig -Encoding UTF8
    Write-Host "   [OK] 設定ファイルを作成しました" -ForegroundColor Green
}

# 設定を読み込み
try {
    $config = Get-Content -Path $mcpConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "   [NG] 設定ファイルの読み込みに失敗しました" -ForegroundColor Red
    exit 1
}

Write-Host "   [OK] 設定ファイルを読み込みました" -ForegroundColor Green
Write-Host ""

# mcpServersプロパティが存在しない場合は作成
if (-not $config.PSObject.Properties.Name -contains "mcpServers") {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

Write-Host "[2] llm-routing MCPサーバーを修正..." -ForegroundColor Yellow

# llm-routingの設定
$llmRoutingConfig = @{
    command = "python"
    args = @("-m", "llm_routing_mcp_server.server")
    env = @{
        MANAOS_INTEGRATION_API_URL = "http://localhost:9500"
        LLM_ROUTING_API_URL = "http://localhost:9501"
    }
    cwd = "C:\Users\mana4\Desktop\manaos_integrations"
}

# 既存の設定を削除（存在する場合）
if ($config.mcpServers.PSObject.Properties.Name -contains "llm-routing") {
    $config.mcpServers.PSObject.Properties.Remove("llm-routing")
}

# 新しい設定を追加
$config.mcpServers | Add-Member -MemberType NoteProperty -Name "llm-routing" -Value $llmRoutingConfig -Force

Write-Host "   [OK] llm-routing を設定しました" -ForegroundColor Green
Write-Host ""

Write-Host "[3] n8n MCPサーバーを修正..." -ForegroundColor Yellow

# n8nの設定（APIキーは空のまま、後で設定）
$n8nConfig = @{
    command = "python"
    args = @("-m", "n8n_mcp_server.server")
    env = @{
        N8N_BASE_URL = "http://100.93.120.33:5678"
        N8N_API_KEY = ""  # 後で設定してください
    }
    cwd = "C:\Users\mana4\Desktop\manaos_integrations"
}

# 既存の設定を削除（存在する場合）
if ($config.mcpServers.PSObject.Properties.Name -contains "n8n") {
    $config.mcpServers.PSObject.Properties.Remove("n8n")
}

# 新しい設定を追加
$config.mcpServers | Add-Member -MemberType NoteProperty -Name "n8n" -Value $n8nConfig -Force

Write-Host "   [OK] n8n を設定しました" -ForegroundColor Green
Write-Host "   ⚠️  N8N_API_KEY が空です。後で設定してください" -ForegroundColor Yellow
Write-Host ""

# 設定を保存
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath -Encoding UTF8
    Write-Host "[4] 設定ファイルを保存しました" -ForegroundColor Green
    Write-Host "   パス: $mcpConfigPath" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] 設定ファイルの保存に失敗しました" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=" * 60
Write-Host "設定完了"
Write-Host "=" * 60
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動してください" -ForegroundColor White
Write-Host "2. 「Tools & MCP」→「Installed MCP Servers」で確認" -ForegroundColor White
Write-Host "3. llm-routing が表示されていればOK" -ForegroundColor Green
Write-Host ""
Write-Host "[n8nのAPIキーを設定する方法]" -ForegroundColor Cyan
Write-Host "1. n8nのWeb UIにアクセス: http://100.93.120.33:5678" -ForegroundColor White
Write-Host "2. Settings → API → Create API Key" -ForegroundColor White
Write-Host "3. APIキーをコピー" -ForegroundColor White
Write-Host "4. 設定ファイルの N8N_API_KEY に設定" -ForegroundColor White
Write-Host ""

















