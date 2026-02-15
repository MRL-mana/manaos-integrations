# ManaOS統合MCPサーバーをCursorのMCP設定に追加するスクリプト

Write-Host "=" * 60
Write-Host "ManaOS統合MCPサーバー Cursor設定追加"
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

# プロジェクトルート（このスクリプトの親ディレクトリ）
$projectRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }

# ManaOS統合MCPサーバーの設定
$manaosConfig = @{
    command = "python"
    args    = @("-m", "manaos_unified_mcp_server.server")
    env     = @{
        COMFYUI_URL                = "http://127.0.0.1:8188"
        MANAOS_INTEGRATION_API_URL = "http://127.0.0.1:9510"
        OBSIDIAN_VAULT_PATH        = $(if ($env:OBSIDIAN_VAULT_PATH) { $env:OBSIDIAN_VAULT_PATH } else { "C:\Users\mana4\Documents\Obsidian Vault" })
    }
    cwd     = $projectRoot
}

# mcpServersプロパティが存在しない場合は作成
if (-not $config.PSObject.Properties.Name -contains "mcpServers") {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

# ManaOS統合MCPサーバーを追加
$config.mcpServers.PSObject.Properties.Add(
    [System.Management.Automation.PSNoteProperty]::new("manaos-unified", $manaosConfig)
)

Write-Host "[2] ManaOS統合MCPサーバーを設定に追加..." -ForegroundColor Yellow

# 設定を保存
try {
    $json = $config | ConvertTo-Json -Depth 10
    Set-Content -Path $mcpConfigPath -Value $json -Encoding UTF8
    Write-Host "   [OK] 設定を追加しました" -ForegroundColor Green
} catch {
    Write-Host "   [NG] 設定の保存に失敗しました: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=" * 60
Write-Host "[OK] 設定完了！" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動してください" -ForegroundColor Yellow
Write-Host "2. Cursorから以下のように使用できます:" -ForegroundColor Yellow
Write-Host "   - svi_generate_video: 動画生成" -ForegroundColor Gray
Write-Host "   - comfyui_generate_image: 画像生成" -ForegroundColor Gray
Write-Host "   - generate_sd_prompt: SD用プロンプト生成（日本語→英語）" -ForegroundColor Gray
Write-Host "   - google_drive_upload: Google Driveアップロード" -ForegroundColor Gray
Write-Host "   - rows_query: Rowsスプレッドシートクエリ" -ForegroundColor Gray
Write-Host "   - obsidian_create_note: Obsidianノート作成" -ForegroundColor Gray
Write-Host "   - image_stock_add: 画像ストック追加" -ForegroundColor Gray
Write-Host "   - notification_send: 通知送信" -ForegroundColor Gray
Write-Host "   - memory_store: 記憶に保存" -ForegroundColor Gray
Write-Host "   - llm_chat: LLMチャット" -ForegroundColor Gray
Write-Host "   - secretary_morning_routine: 朝のルーチン" -ForegroundColor Gray
Write-Host ""
