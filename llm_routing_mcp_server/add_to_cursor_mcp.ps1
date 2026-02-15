# LLMルーティングMCPサーバーをCursorのMCP設定に追加するスクリプト

Write-Host "=" * 60
Write-Host "LLMルーティングMCPサーバー Cursor設定追加"
Write-Host "=" * 60
Write-Host ""

$mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

Write-Host "[1] MCP設定ファイルの確認..." -ForegroundColor Yellow

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
    Write-Host "   設定ファイルを作成しました" -ForegroundColor Green
}

# 設定を読み込み
try {
    $config = Get-Content -Path $mcpConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "   [NG] 設定ファイルの読み込みに失敗しました" -ForegroundColor Red
    Write-Host "   手動で設定してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "   [OK] 設定ファイルを読み込みました" -ForegroundColor Green
Write-Host ""

# LLMルーティングMCPサーバーの設定
$workspacePath = "C:\Users\mana4\Desktop\manaos_integrations"
$llmRoutingConfig = @{
    command = "python"
    args = @("-m", "llm_routing_mcp_server.server")
    env = @{
        MANAOS_INTEGRATION_API_URL = "http://127.0.0.1:9502"
        PORT = "5111"
        PYTHONPATH = $workspacePath
    }
    cwd = $workspacePath
}

# mcpServersプロパティが存在しない場合は作成
if (-not $config.PSObject.Properties.Name -contains "mcpServers") {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

# LLMルーティングMCPサーバーを追加
if ($config.mcpServers.PSObject.Properties.Name -contains "llm-routing") {
    Write-Host "[2] LLMルーティングMCPサーバーが既に設定されています" -ForegroundColor Yellow
    Write-Host "   更新しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
    $updateInput = Read-Host
    if ($updateInput -eq "y") {
        $config.mcpServers."llm-routing" = $llmRoutingConfig
        Write-Host "   [OK] 設定を更新しました" -ForegroundColor Green
    } else {
        Write-Host "   設定をスキップしました" -ForegroundColor Gray
        exit 0
    }
} else {
    $config.mcpServers | Add-Member -MemberType NoteProperty -Name "llm-routing" -Value $llmRoutingConfig
    Write-Host "[2] LLMルーティングMCPサーバーを設定に追加..." -ForegroundColor Yellow
    Write-Host "   [OK] 設定を追加しました" -ForegroundColor Green
}

# 設定を保存
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath -Encoding UTF8
    Write-Host ""
    Write-Host "[3] 設定ファイルを保存しました" -ForegroundColor Green
    Write-Host "   パス: $mcpConfigPath" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] 設定ファイルの保存に失敗しました" -ForegroundColor Red
    Write-Host "   手動で設定してください" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=" * 60
Write-Host "設定完了"
Write-Host "=" * 60
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動" -ForegroundColor White
Write-Host "2. Cursorでチャットを開く" -ForegroundColor White
Write-Host "3. 以下のツールが利用可能になります:" -ForegroundColor White
Write-Host "   - analyze_llm_difficulty: プロンプトの難易度を分析" -ForegroundColor Gray
Write-Host "   - route_llm_request: LLMリクエストをルーティング" -ForegroundColor Gray
Write-Host "   - get_available_models: 利用可能なモデル一覧を取得" -ForegroundColor Gray
Write-Host ""
Write-Host "[使用例]" -ForegroundColor Cyan
Write-Host "Cursorのチャットで:" -ForegroundColor White
Write-Host '  "この関数のタイポを修正して" というプロンプトの難易度を分析して' -ForegroundColor Gray
Write-Host ""
Write-Host "Cursorが自動的に analyze_llm_difficulty ツールを呼び出します" -ForegroundColor Green
Write-Host ""







