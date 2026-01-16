# n8n APIキーを自動的に設定するスクリプト（既存のAPIキーを自動使用）

Write-Host "=" * 60
Write-Host "n8n APIキー自動設定スクリプト（自動モード）"
Write-Host "=" * 60
Write-Host ""

# 設定ファイルのパス
$oldConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
$newConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

$apiKey = $null
$baseUrl = "http://100.93.120.33:5678"

Write-Host "[1] 既存のAPIキーを確認中..." -ForegroundColor Yellow
Write-Host ""

# 古い設定ファイルからAPIキーを取得
if (Test-Path $oldConfigPath) {
    try {
        $oldConfig = Get-Content $oldConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($oldConfig.mcpServers.n8n -and $oldConfig.mcpServers.n8n.env.N8N_API_KEY) {
            $apiKey = $oldConfig.mcpServers.n8n.env.N8N_API_KEY
            $oldBaseUrl = $oldConfig.mcpServers.n8n.env.N8N_BASE_URL
            Write-Host "  ✅ 古い設定ファイルからAPIキーを発見しました" -ForegroundColor Green
            Write-Host "     APIキー: $($apiKey.Substring(0, [Math]::Min(30, $apiKey.Length)))..." -ForegroundColor Gray
            Write-Host "     古いN8N_BASE_URL: $oldBaseUrl" -ForegroundColor Gray
            Write-Host "     新しいN8N_BASE_URL: $baseUrl" -ForegroundColor Gray
            Write-Host ""
            Write-Host "  ⚠️  注意: N8N_BASE_URLを $oldBaseUrl から $baseUrl に変更します" -ForegroundColor Yellow
            Write-Host "     このAPIキーが $baseUrl で有効か確認してください" -ForegroundColor Yellow
        } else {
            Write-Host "  ⚠️  古い設定ファイルにAPIキーが見つかりません" -ForegroundColor Yellow
            Write-Host "     手動でAPIキーを設定する必要があります" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "  ❌ 古い設定ファイルの読み込みエラー: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ❌ 古い設定ファイルが見つかりません" -ForegroundColor Red
    Write-Host "     手動でAPIキーを設定する必要があります" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2] 新しい設定ファイルを更新中..." -ForegroundColor Yellow
Write-Host ""

# 新しい設定ファイルを更新
if (-not (Test-Path $newConfigPath)) {
    Write-Host "  ⚠️  設定ファイルが見つかりません。作成します..." -ForegroundColor Yellow
    $configDir = Split-Path -Parent $newConfigPath
    if (-not (Test-Path $configDir)) {
        New-Item -Path $configDir -ItemType Directory -Force | Out-Null
    }
    $defaultConfig = @{
        mcpServers = @{}
    } | ConvertTo-Json -Depth 10
    Set-Content -Path $newConfigPath -Value $defaultConfig -Encoding UTF8
}

try {
    $config = Get-Content $newConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    
    if (-not $config.mcpServers) {
        $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
    }
    
    if (-not $config.mcpServers.n8n) {
        $config.mcpServers | Add-Member -MemberType NoteProperty -Name "n8n" -Value @{
            command = "python"
            args = @("-m", "n8n_mcp_server.server")
            env = @{}
            cwd = "C:\Users\mana4\Desktop\manaos_integrations"
        }
    }
    
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    
    $config.mcpServers.n8n.env.N8N_BASE_URL = $baseUrl
    $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
    
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $newConfigPath -Encoding UTF8
    
    Write-Host "  ✅ 設定ファイルを更新しました" -ForegroundColor Green
    Write-Host "     パス: $newConfigPath" -ForegroundColor Gray
    Write-Host "     N8N_BASE_URL: $baseUrl" -ForegroundColor Gray
    Write-Host "     N8N_API_KEY: $($apiKey.Substring(0, [Math]::Min(30, $apiKey.Length)))..." -ForegroundColor Gray
} catch {
    Write-Host "  ❌ エラー: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3] 設定を確認中..." -ForegroundColor Yellow
Write-Host ""

try {
    $config = Get-Content $newConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.mcpServers.n8n -and $config.mcpServers.n8n.env.N8N_API_KEY) {
        Write-Host "  ✅ APIキーが正しく設定されました" -ForegroundColor Green
        Write-Host "     N8N_BASE_URL: $($config.mcpServers.n8n.env.N8N_BASE_URL)" -ForegroundColor Gray
        Write-Host "     N8N_API_KEY: 設定済み (長さ: $($config.mcpServers.n8n.env.N8N_API_KEY.Length)文字)" -ForegroundColor Gray
    } else {
        Write-Host "  ❌ APIキーが設定されていません" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ 確認中にエラーが発生しました: $($_.Exception.Message)" -ForegroundColor Red
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
Write-Host "3. n8nのエラーが解消されていればOK" -ForegroundColor Green
Write-Host ""
Write-Host "[注意]" -ForegroundColor Yellow
Write-Host "- N8N_BASE_URL は $baseUrl に設定されました" -ForegroundColor Gray
Write-Host "- このAPIキーが $baseUrl で有効か確認してください" -ForegroundColor Gray
Write-Host "- エラーが続く場合は、$baseUrl で新しいAPIキーを作成してください" -ForegroundColor Gray
Write-Host ""

















