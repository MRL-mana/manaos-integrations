# 統合版manaos_mcp_server.pyをCursorのMCP設定に追加

Write-Host "=== Cursor MCP設定に追加 ===" -ForegroundColor Cyan
Write-Host ""

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"

# MCP設定ファイルを読み込み
if (Test-Path $mcpConfigPath) {
    $config = Get-Content $mcpConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    Write-Host "[INFO] MCP設定ファイルが見つかりません。新規作成します。" -ForegroundColor Yellow
    $config = @{
        mcpServers = @{}
    } | ConvertTo-Json -Depth 10 | ConvertFrom-Json
}

# 統合版manaos_mcp_server.pyの設定を追加
$manaosUnifiedConfig = @{
    command = "python"
    args = @(
        "C:\Users\mana4\Desktop\manaos_integrations\konoha_mcp_servers\archive_20251106\manaos_mcp_server.py"
    )
    env = @{
        PYTHONPATH = "C:\Users\mana4\Desktop\manaos_integrations"
        MANAOS_INTEGRATION_API_URL = "http://127.0.0.1:9510"
        COMFYUI_URL = "http://127.0.0.1:8188"
        OBSIDIAN_VAULT_PATH = "C:\Users\mana4\Documents\Obsidian Vault"
    }
    cwd = "C:\Users\mana4\Desktop\manaos_integrations"
}

# mcpServersプロパティが存在しない場合は作成
if (-not $config.PSObject.Properties.Name -contains "mcpServers") {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

# manaos-unified-konohaを追加（既存のmanaos-unifiedと区別）
if ($config.mcpServers.PSObject.Properties.Name -contains "manaos-unified-konoha") {
    Write-Host "[INFO] manaos-unified-konohaは既に設定されています。更新します。" -ForegroundColor Yellow
}

$config.mcpServers | Add-Member -MemberType NoteProperty -Name "manaos-unified-konoha" -Value $manaosUnifiedConfig -Force

# 設定ファイルを保存
$config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath -Encoding UTF8

Write-Host "[OK] manaos-unified-konohaをMCP設定に追加しました！" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  1. Cursorを再起動してください" -ForegroundColor Yellow
Write-Host "  2. Cursorのチャットで以下を試してください:" -ForegroundColor Yellow
Write-Host "     'manaos-unified-konohaのツール一覧を取得してください'" -ForegroundColor Gray

