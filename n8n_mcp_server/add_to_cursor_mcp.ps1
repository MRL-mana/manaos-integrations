# CursorのMCP設定にn8n MCPサーバーを追加するスクリプト

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
$mcpConfigDir = Split-Path $mcpConfigPath -Parent

# ディレクトリが存在しない場合は作成
if (-not (Test-Path $mcpConfigDir)) {
    New-Item -ItemType Directory -Path $mcpConfigDir -Force | Out-Null
}

# 既存の設定を読み込む
if (Test-Path $mcpConfigPath) {
    $jsonContent = Get-Content $mcpConfigPath -Raw
    $config = $jsonContent | ConvertFrom-Json
} else {
    $config = @{
        mcpServers = @{}
    } | ConvertTo-Json | ConvertFrom-Json
}

# n8n MCPサーバーを追加（PSCustomObjectとして作成）
$n8nServer = [PSCustomObject]@{
    command = "python"
    args = @(
        "-m",
        "n8n_mcp_server.server"
    )
    env = [PSCustomObject]@{
        N8N_BASE_URL = "http://100.93.120.33:5678"
        N8N_API_KEY = ""  # ここにAPIキーを設定してください
    }
    cwd = "C:\Users\mana4\Desktop\manaos_integrations"
}

# mcpServersオブジェクトに追加
if (-not $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

$config.mcpServers | Add-Member -MemberType NoteProperty -Name "n8n" -Value $n8nServer -Force

# JSONに変換して保存
$json = $config | ConvertTo-Json -Depth 10
$json | Set-Content $mcpConfigPath -Encoding UTF8

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Cursor MCP設定にn8n MCPサーバーを追加しました" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "設定ファイル: $mcpConfigPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. n8nのWeb UIにアクセス: http://100.93.120.33:5678" -ForegroundColor White
Write-Host "2. Settings → API → Create API Key" -ForegroundColor White
Write-Host "3. APIキーをコピー" -ForegroundColor White
Write-Host "4. 設定ファイルの N8N_API_KEY に設定" -ForegroundColor White
Write-Host "5. Cursorを再起動" -ForegroundColor White
Write-Host ""
Write-Host "[使用方法]" -ForegroundColor Cyan
Write-Host "Cursorのチャットで以下を入力:" -ForegroundColor White
Write-Host "  n8n_import_workflow を使って、n8n_workflow_template.json をインポートしてください" -ForegroundColor Yellow
Write-Host ""

