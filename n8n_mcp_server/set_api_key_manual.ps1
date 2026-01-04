# n8n APIキーを手動で設定するスクリプト（対話型）

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    [string]$BaseUrl = "http://localhost:5679"
)

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n APIキー設定" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 設定ファイルを読み込む
if (-not (Test-Path $mcpConfigPath)) {
    Write-Host "[NG] MCP設定ファイルが見つかりません: $mcpConfigPath" -ForegroundColor Red
    exit 1
}

$jsonContent = Get-Content $mcpConfigPath -Raw
$config = $jsonContent | ConvertFrom-Json

# APIキーとBase URLを設定
if ($config.mcpServers.n8n) {
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n.env = @{}
    }
    $config.mcpServers.n8n.env.N8N_API_KEY = $ApiKey
    $config.mcpServers.n8n.env.N8N_BASE_URL = $BaseUrl
    
    # JSONに変換して保存
    $json = $config | ConvertTo-Json -Depth 10
    $json | Set-Content $mcpConfigPath -Encoding UTF8
    
    Write-Host "[OK] APIキーとBase URLを設定しました" -ForegroundColor Green
    Write-Host "  Base URL: $BaseUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Cursorを再起動して、MCPサーバーに接続してください。" -ForegroundColor Yellow
} else {
    Write-Host "[NG] n8n MCPサーバーの設定が見つかりません" -ForegroundColor Red
    Write-Host "先に add_to_cursor_mcp.ps1 を実行してください。" -ForegroundColor Yellow
    exit 1
}


