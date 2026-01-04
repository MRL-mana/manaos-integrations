# n8n APIキーを設定するスクリプト

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n APIキー設定" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# APIキーを入力
Write-Host "n8nのAPIキーを入力してください:" -ForegroundColor Yellow
Write-Host "(n8nのWeb UI: http://100.93.120.33:5678 → Settings → API → Create API Key)" -ForegroundColor Gray
Write-Host ""
$apiKey = Read-Host "APIキー"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[NG] APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

# 設定ファイルを読み込む
if (-not (Test-Path $mcpConfigPath)) {
    Write-Host "[NG] MCP設定ファイルが見つかりません: $mcpConfigPath" -ForegroundColor Red
    exit 1
}

$jsonContent = Get-Content $mcpConfigPath -Raw
$config = $jsonContent | ConvertFrom-Json

# APIキーを設定
if ($config.mcpServers.n8n) {
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
    
    # JSONに変換して保存
    $json = $config | ConvertTo-Json -Depth 10
    $json | Set-Content $mcpConfigPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "[OK] APIキーを設定しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "Cursorを再起動して、MCPサーバーに接続してください。" -ForegroundColor Yellow
} else {
    Write-Host "[NG] n8n MCPサーバーの設定が見つかりません" -ForegroundColor Red
    Write-Host "先に add_to_cursor_mcp.ps1 を実行してください。" -ForegroundColor Yellow
    exit 1
}
















