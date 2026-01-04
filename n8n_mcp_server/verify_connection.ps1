# n8n MCPサーバー接続確認スクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n MCPサーバー 接続確認" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. MCP設定ファイルの確認
Write-Host "[1/5] MCP設定ファイルを確認中..." -ForegroundColor Yellow
$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
if (Test-Path $mcpConfigPath) {
    $config = Get-Content $mcpConfigPath | ConvertFrom-Json
    if ($config.mcpServers.n8n) {
        Write-Host "[OK] n8n MCPサーバーの設定が見つかりました" -ForegroundColor Green
        Write-Host "  - command: $($config.mcpServers.n8n.command)" -ForegroundColor Gray
        Write-Host "  - cwd: $($config.mcpServers.n8n.cwd)" -ForegroundColor Gray
        if ($config.mcpServers.n8n.env.N8N_API_KEY) {
            Write-Host "  - N8N_API_KEY: 設定済み" -ForegroundColor Green
        } else {
            Write-Host "  - N8N_API_KEY: 未設定" -ForegroundColor Red
        }
    } else {
        Write-Host "[NG] n8n MCPサーバーの設定が見つかりません" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[NG] MCP設定ファイルが見つかりません: $mcpConfigPath" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. n8nサーバーの確認
Write-Host "[2/5] n8nサーバーに接続確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://100.93.120.33:5678/healthz" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] n8nサーバーは起動しています" -ForegroundColor Green
    }
} catch {
    Write-Host "[NG] n8nサーバーに接続できません: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 3. Pythonモジュールの確認
Write-Host "[3/5] Pythonモジュールを確認中..." -ForegroundColor Yellow
$integrationsDir = "C:\Users\mana4\Desktop\manaos_integrations"
Push-Location $integrationsDir
try {
    $result = python -c "import n8n_mcp_server.server; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] MCPサーバーモジュールをインポートできました" -ForegroundColor Green
    } else {
        Write-Host "[NG] MCPサーバーモジュールのインポートに失敗: $result" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[NG] Pythonの実行に失敗: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

Write-Host ""

# 4. MCPパッケージの確認
Write-Host "[4/5] MCPパッケージを確認中..." -ForegroundColor Yellow
try {
    $result = python -c "import mcp; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] MCPパッケージがインストールされています" -ForegroundColor Green
    } else {
        Write-Host "[NG] MCPパッケージが見つかりません: $result" -ForegroundColor Red
        Write-Host "  インストール: pip install mcp requests" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[NG] MCPパッケージの確認に失敗: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 5. 環境変数の確認
Write-Host "[5/5] 環境変数を確認中..." -ForegroundColor Yellow
$config = Get-Content $mcpConfigPath | ConvertFrom-Json
if ($config.mcpServers.n8n.env.N8N_BASE_URL) {
    Write-Host "[OK] N8N_BASE_URL: $($config.mcpServers.n8n.env.N8N_BASE_URL)" -ForegroundColor Green
} else {
    Write-Host "[NG] N8N_BASE_URLが設定されていません" -ForegroundColor Red
}

if ($config.mcpServers.n8n.env.N8N_API_KEY) {
    $apiKeyLength = $config.mcpServers.n8n.env.N8N_API_KEY.Length
    Write-Host "[OK] N8N_API_KEY: 設定済み (長さ: $apiKeyLength)" -ForegroundColor Green
} else {
    Write-Host "[NG] N8N_API_KEYが設定されていません" -ForegroundColor Red
    Write-Host "  n8nのWeb UIからAPIキーを作成してください:" -ForegroundColor Yellow
    Write-Host "  http://100.93.120.33:5678 → Settings → API → Create API Key" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "確認完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CursorでMCPサーバーに接続できるか確認してください。" -ForegroundColor Yellow
Write-Host "接続エラーが続く場合は、Cursorの開発者ツール（Ctrl+Shift+I）で" -ForegroundColor Yellow
Write-Host "MCP関連のエラーログを確認してください。" -ForegroundColor Yellow
















