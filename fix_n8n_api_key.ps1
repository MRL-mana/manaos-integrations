# n8n APIキーを統一して設定するスクリプト

Write-Host "=" * 60
Write-Host "n8n APIキー統一設定スクリプト"
Write-Host "=" * 60
Write-Host ""

# 設定ファイルのパス
$mcpConfigPath1 = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
$mcpConfigPath2 = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "[1] 現在の設定を確認中..." -ForegroundColor Yellow
Write-Host ""

# APIキーを入力
Write-Host "n8nのAPIキーを入力してください:" -ForegroundColor Cyan
Write-Host "(n8nのWeb UI: http://100.93.120.33:5678 → Settings → API → Create API Key)" -ForegroundColor Gray
Write-Host "(または http://localhost:5678 でローカルのn8nを使用する場合)" -ForegroundColor Gray
Write-Host ""
$apiKey = Read-Host "APIキー"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[NG] APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2] MCP設定ファイルを更新中..." -ForegroundColor Yellow
Write-Host ""

# 設定ファイル1を更新
if (Test-Path $mcpConfigPath1) {
    Write-Host "  設定ファイル1を更新: $mcpConfigPath1" -ForegroundColor Cyan
    try {
        $config = Get-Content $mcpConfigPath1 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config.mcpServers.n8n) {
            if (-not $config.mcpServers.n8n.env) {
                $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
            }
            $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
            
            $config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath1 -Encoding UTF8
            Write-Host "    ✅ 更新完了" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  n8nの設定が見つかりません" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    ❌ エラー: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  設定ファイル1が見つかりません: $mcpConfigPath1" -ForegroundColor Yellow
}

# 設定ファイル2を更新
if (Test-Path $mcpConfigPath2) {
    Write-Host "  設定ファイル2を更新: $mcpConfigPath2" -ForegroundColor Cyan
    try {
        $config = Get-Content $mcpConfigPath2 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config.mcpServers.n8n) {
            if (-not $config.mcpServers.n8n.env) {
                $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
            }
            $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
            
            $config | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath2 -Encoding UTF8
            Write-Host "    ✅ 更新完了" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  n8nの設定が見つかりません" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    ❌ エラー: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  設定ファイル2が見つかりません: $mcpConfigPath2" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] 設定を確認中..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path $mcpConfigPath1) {
    $config = Get-Content $mcpConfigPath1 -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.mcpServers.n8n -and $config.mcpServers.n8n.env.N8N_API_KEY) {
        Write-Host "  ✅ 設定ファイル1: APIキーが設定されています" -ForegroundColor Green
        Write-Host "     N8N_BASE_URL: $($config.mcpServers.n8n.env.N8N_BASE_URL)" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  設定ファイル1: APIキーが設定されていません" -ForegroundColor Yellow
    }
}

if (Test-Path $mcpConfigPath2) {
    $config = Get-Content $mcpConfigPath2 -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.mcpServers.n8n -and $config.mcpServers.n8n.env.N8N_API_KEY) {
        Write-Host "  ✅ 設定ファイル2: APIキーが設定されています" -ForegroundColor Green
        Write-Host "     N8N_BASE_URL: $($config.mcpServers.n8n.env.N8N_BASE_URL)" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  設定ファイル2: APIキーが設定されていません" -ForegroundColor Yellow
    }
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
Write-Host "- 複数の設定ファイルがある場合、Cursorは通常、以下の順序で読み込みます:" -ForegroundColor Gray
Write-Host "  1. $mcpConfigPath1" -ForegroundColor Gray
Write-Host "  2. $mcpConfigPath2" -ForegroundColor Gray
Write-Host "- 両方のファイルに同じAPIキーを設定することを推奨します" -ForegroundColor Gray
Write-Host ""

















