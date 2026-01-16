# このはサーバー側のBrave Search APIキーをローカルのMCP設定に追加するスクリプト

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Brave Search APIキーをMCP設定に追加" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
$mcpConfigDir = Split-Path $mcpConfigPath -Parent

# ディレクトリが存在しない場合は作成
if (-not (Test-Path $mcpConfigDir)) {
    New-Item -ItemType Directory -Path $mcpConfigDir -Force | Out-Null
    Write-Host "[OK] MCP設定ディレクトリを作成しました: $mcpConfigDir" -ForegroundColor Green
}

# このはサーバー側からBrave Search APIキーを取得
Write-Host "[1] このはサーバー側からBrave Search APIキーを取得中..." -ForegroundColor Yellow
Write-Host ""

$braveApiKey = $null

try {
    # SSH経由で環境変数を取得
    $envOutput = ssh konoha "env | grep BRAVE_API_KEY" 2>&1
    
    if ($LASTEXITCODE -eq 0 -and $envOutput -match "BRAVE_API_KEY=(.+)") {
        $braveApiKey = $matches[1]
        Write-Host "  [OK] Brave Search APIキーを取得しました" -ForegroundColor Green
        Write-Host "  APIキー: $($braveApiKey.Substring(0, [Math]::Min(10, $braveApiKey.Length)))..." -ForegroundColor Gray
    } else {
        Write-Host "  [WARN] SSH経由での取得に失敗しました" -ForegroundColor Yellow
        Write-Host "  手動でAPIキーを入力してください" -ForegroundColor Yellow
        Write-Host ""
        $braveApiKey = Read-Host "Brave Search APIキーを入力してください"
    }
} catch {
    Write-Host "  [WARN] SSH接続に失敗しました: $_" -ForegroundColor Yellow
    Write-Host "  手動でAPIキーを入力してください" -ForegroundColor Yellow
    Write-Host ""
    $braveApiKey = Read-Host "Brave Search APIキーを入力してください"
}

if ([string]::IsNullOrWhiteSpace($braveApiKey)) {
    Write-Host "[ERROR] APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 既存の設定を読み込む
Write-Host "[2] MCP設定ファイルを読み込み中..." -ForegroundColor Yellow

if (Test-Path $mcpConfigPath) {
    try {
        $jsonContent = Get-Content $mcpConfigPath -Raw -Encoding UTF8
        $config = $jsonContent | ConvertFrom-Json
        Write-Host "  [OK] 既存の設定ファイルを読み込みました" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] 設定ファイルの読み込みに失敗しました。新規作成します。" -ForegroundColor Yellow
        $config = @{
            mcpServers = @{}
        } | ConvertTo-Json | ConvertFrom-Json
    }
} else {
    Write-Host "  [INFO] 設定ファイルが存在しません。新規作成します。" -ForegroundColor Yellow
    $config = @{
        mcpServers = @{}
    } | ConvertTo-Json | ConvertFrom-Json
}

# mcpServersプロパティが存在しない場合は作成
if (-not $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
}

Write-Host ""

# Brave Search APIキーを各MCPサーバーの環境変数に追加
Write-Host "[3] Brave Search APIキーをMCP設定に追加中..." -ForegroundColor Yellow

$updated = $false

# 各MCPサーバーに環境変数を追加
foreach ($serverName in $config.mcpServers.PSObject.Properties.Name) {
    $server = $config.mcpServers.$serverName
    
    # envプロパティが存在しない場合は作成
    if (-not $server.env) {
        $server | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    
    # BRAVE_API_KEYを追加または更新
    if (-not $server.env.BRAVE_API_KEY -or $server.env.BRAVE_API_KEY -ne $braveApiKey) {
        $server.env | Add-Member -MemberType NoteProperty -Name "BRAVE_API_KEY" -Value $braveApiKey -Force
        Write-Host "  [OK] $serverName にBRAVE_API_KEYを追加しました" -ForegroundColor Green
        $updated = $true
    } else {
        Write-Host "  [INFO] $serverName には既にBRAVE_API_KEYが設定されています" -ForegroundColor Gray
    }
}

# もしMCPサーバーが存在しない場合、.envファイルにも追加
Write-Host ""
Write-Host "[4] .envファイルにも追加中..." -ForegroundColor Yellow

$envPath = Join-Path $PSScriptRoot ".env"
$envPathKonoha = Join-Path $PSScriptRoot "konoha_mcp_servers\.env"

# メインの.envファイル
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    if ($envContent -notmatch "BRAVE_API_KEY=") {
        Add-Content -Path $envPath -Value "`nBRAVE_API_KEY=$braveApiKey"
        Write-Host "  [OK] .envファイルに追加しました: $envPath" -ForegroundColor Green
    } else {
        # 既存の値を更新
        $envContent = $envContent -replace "BRAVE_API_KEY=.*", "BRAVE_API_KEY=$braveApiKey"
        Set-Content -Path $envPath -Value $envContent -Encoding UTF8
        Write-Host "  [OK] .envファイルを更新しました: $envPath" -ForegroundColor Green
    }
} else {
    Set-Content -Path $envPath -Value "BRAVE_API_KEY=$braveApiKey" -Encoding UTF8
    Write-Host "  [OK] .envファイルを作成しました: $envPath" -ForegroundColor Green
}

# konoha_mcp_servers/.envファイル
if (Test-Path $envPathKonoha) {
    $envContentKonoha = Get-Content $envPathKonoha -Raw
    if ($envContentKonoha -notmatch "BRAVE_API_KEY=") {
        Add-Content -Path $envPathKonoha -Value "`nBRAVE_API_KEY=$braveApiKey"
        Write-Host "  [OK] konoha_mcp_servers/.envファイルに追加しました" -ForegroundColor Green
    } else {
        $envContentKonoha = $envContentKonoha -replace "BRAVE_API_KEY=.*", "BRAVE_API_KEY=$braveApiKey"
        Set-Content -Path $envPathKonoha -Value $envContentKonoha -Encoding UTF8
        Write-Host "  [OK] konoha_mcp_servers/.envファイルを更新しました" -ForegroundColor Green
    }
} else {
    $konohaEnvDir = Split-Path $envPathKonoha -Parent
    if (-not (Test-Path $konohaEnvDir)) {
        New-Item -ItemType Directory -Path $konohaEnvDir -Force | Out-Null
    }
    Set-Content -Path $envPathKonoha -Value "BRAVE_API_KEY=$braveApiKey" -Encoding UTF8
    Write-Host "  [OK] konoha_mcp_servers/.envファイルを作成しました" -ForegroundColor Green
}

Write-Host ""

# JSONに変換して保存
if ($updated) {
    Write-Host "[5] MCP設定ファイルを保存中..." -ForegroundColor Yellow
    $json = $config | ConvertTo-Json -Depth 10
    $json | Set-Content $mcpConfigPath -Encoding UTF8
    Write-Host "  [OK] MCP設定ファイルを保存しました: $mcpConfigPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "完了" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動してMCP設定を反映してください" -ForegroundColor White
Write-Host "2. Brave Search APIを使用するMCPサーバーが動作することを確認してください" -ForegroundColor White
Write-Host ""
Write-Host "設定ファイルの場所:" -ForegroundColor Yellow
Write-Host "  MCP設定: $mcpConfigPath" -ForegroundColor Gray
Write-Host "  .env: $envPath" -ForegroundColor Gray
Write-Host "  konoha_mcp_servers/.env: $envPathKonoha" -ForegroundColor Gray
Write-Host ""



