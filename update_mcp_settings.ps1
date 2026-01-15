# CursorのMCP設定ファイルを更新するスクリプト

Write-Host "=== CursorのMCP設定ファイルを更新 ===" -ForegroundColor Cyan
Write-Host ""

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
$oldPath = "C:\Users\mana4\OneDrive\Desktop\manaos_integrations"
$newPath = "C:\Users\mana4\Desktop\manaos_integrations"

if (-not (Test-Path $mcpConfigPath)) {
    Write-Host "[INFO] MCP設定ファイルが見つかりません: $mcpConfigPath" -ForegroundColor Yellow
    Write-Host "[INFO] 新しいワークスペースでMCPサーバーを設定してください" -ForegroundColor Yellow
    exit 0
}

Write-Host "[INFO] MCP設定ファイルを読み込み中..." -ForegroundColor Yellow
try {
    $config = Get-Content $mcpConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "[ERROR] 設定ファイルの読み込みに失敗しました: $_" -ForegroundColor Red
    exit 1
}

$updated = $false

if ($config.mcpServers) {
    Write-Host "[INFO] MCPサーバー設定を確認中..." -ForegroundColor Yellow
    
    foreach ($server in $config.mcpServers.PSObject.Properties) {
        if ($server.Value.cwd -like "*OneDrive*") {
            Write-Host "  更新: $($server.Name)" -ForegroundColor Yellow
            Write-Host "    旧: $($server.Value.cwd)" -ForegroundColor Gray
            $server.Value.cwd = $server.Value.cwd -replace [regex]::Escape($oldPath), $newPath
            Write-Host "    新: $($server.Value.cwd)" -ForegroundColor Green
            $updated = $true
        }
    }
}

if ($updated) {
    Write-Host ""
    Write-Host "[INFO] 設定ファイルを保存中..." -ForegroundColor Yellow
    try {
        $json = $config | ConvertTo-Json -Depth 10
        Set-Content -Path $mcpConfigPath -Value $json -Encoding UTF8
        Write-Host "[OK] MCP設定ファイルを更新しました" -ForegroundColor Green
        Write-Host ""
        Write-Host "[次のステップ]" -ForegroundColor Cyan
        Write-Host "1. Cursorを再起動してください" -ForegroundColor Yellow
        Write-Host "2. MCPサーバーが正常に動作するか確認してください" -ForegroundColor Yellow
    } catch {
        Write-Host "[ERROR] 設定ファイルの保存に失敗しました: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] 更新が必要な設定はありませんでした" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 完了 ===" -ForegroundColor Cyan


