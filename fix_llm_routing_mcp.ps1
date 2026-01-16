# llm-routing MCPサーバーの設定を強制的に追加・更新するスクリプト

Write-Host "=" * 60
Write-Host "llm-routing MCPサーバー設定の強制更新"
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

# LLMルーティングMCPサーバーの設定
$llmRoutingConfig = @{
    command = "python"
    args = @("-m", "llm_routing_mcp_server.server")
    env = @{
        MANAOS_INTEGRATION_API_URL = "http://localhost:9500"
        LLM_ROUTING_API_URL = "http://localhost:9501"
    }
    cwd = "C:\Users\mana4\Desktop\manaos_integrations"
}

Write-Host "[2] llm-routing MCPサーバーを設定に追加/更新..." -ForegroundColor Yellow

# 既存の設定を削除（存在する場合）
if ($config.mcpServers.PSObject.Properties.Name -contains "llm-routing") {
    $config.mcpServers.PSObject.Properties.Remove("llm-routing")
    Write-Host "   既存の設定を削除しました" -ForegroundColor Gray
}

# 新しい設定を追加
$config.mcpServers | Add-Member -MemberType NoteProperty -Name "llm-routing" -Value $llmRoutingConfig -Force

Write-Host "   [OK] 設定を追加しました" -ForegroundColor Green
Write-Host ""

# 設定を保存
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath -Encoding UTF8
    Write-Host "[3] 設定ファイルを保存しました" -ForegroundColor Green
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
Write-Host "[設定内容]" -ForegroundColor Cyan
Write-Host "  コマンド: python" -ForegroundColor Gray
Write-Host "  引数: -m llm_routing_mcp_server.server" -ForegroundColor Gray
Write-Host "  作業ディレクトリ: C:\Users\mana4\Desktop\manaos_integrations" -ForegroundColor Gray
Write-Host ""


















