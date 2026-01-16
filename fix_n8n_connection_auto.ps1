# n8n接続問題の自動解決スクリプト（非対話モード対応）
# ローカルn8nサーバーを起動して設定を自動更新

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     n8n接続問題の自動解決                                        ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 設定ファイルのパス
$mcpConfigPath1 = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
$mcpConfigPath2 = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "[1] 接続状況の確認..." -ForegroundColor Yellow
Write-Host ""

# ローカルサーバーの確認
$useLocal = $false
$localPort = 5678

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   ✅ ローカルn8nサーバー (ポート5678) に接続可能" -ForegroundColor Green
    $useLocal = $true
    $localPort = 5678
} catch {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5679/healthz" -Method GET -TimeoutSec 2 -ErrorAction Stop
        Write-Host "   ✅ ローカルn8nサーバー (ポート5679) に接続可能" -ForegroundColor Green
        $useLocal = $true
        $localPort = 5679
    } catch {
        Write-Host "   ⚠️  ローカルn8nサーバーが起動していません" -ForegroundColor Yellow
    }
}

Write-Host ""

# ローカルサーバーが起動していない場合、起動を試みる
if (-not $useLocal) {
    Write-Host "[2] ローカルn8nサーバーを起動します..." -ForegroundColor Yellow
    Write-Host ""
    
    # n8nがインストールされているか確認
    $n8nInstalled = Get-Command n8n -ErrorAction SilentlyContinue
    if (-not $n8nInstalled) {
        Write-Host "   ❌ n8nがインストールされていません" -ForegroundColor Red
        Write-Host "   まず n8n をインストールしてください: npm install -g n8n" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "   ✅ n8nがインストールされています" -ForegroundColor Green
    
    # 既存のn8nプロセスを確認
    $existingProcesses = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { 
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*n8n*"
    }
    
    if ($existingProcesses) {
        Write-Host "   ⚠️  既存のn8nプロセスが見つかりました" -ForegroundColor Yellow
        Write-Host "   PID: $($existingProcesses.Id -join ', ')" -ForegroundColor Gray
    } else {
        # n8nを起動（バックグラウンド）
        Write-Host "   n8nサーバーを起動中..." -ForegroundColor Gray
        
        if (Test-Path "start_n8n_local.ps1") {
            # 別ウィンドウで起動
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; .\start_n8n_local.ps1" -WindowStyle Minimized
            Write-Host "   ✅ n8nサーバーを起動しました（別ウィンドウ）" -ForegroundColor Green
        } else {
            # 直接起動
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; n8n start --port 5679" -WindowStyle Minimized
            Write-Host "   ✅ n8nサーバーを起動しました（ポート5679、別ウィンドウ）" -ForegroundColor Green
            $localPort = 5679
        }
        
        Write-Host "   10秒待機してから接続を確認します..." -ForegroundColor Gray
        Start-Sleep -Seconds 10
        
        # 接続確認
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$localPort/healthz" -Method GET -TimeoutSec 5 -ErrorAction Stop
            Write-Host "   ✅ ローカルn8nサーバーに接続できました" -ForegroundColor Green
            $useLocal = $true
        } catch {
            Write-Host "   ⚠️  まだ起動中の可能性があります" -ForegroundColor Yellow
            Write-Host "   手動で確認してください: http://localhost:$localPort" -ForegroundColor Gray
            $useLocal = $true  # 設定は更新する
        }
    }
}

Write-Host ""
Write-Host "[3] MCP設定ファイルを更新..." -ForegroundColor Yellow

# 使用するURLを決定
if ($useLocal) {
    $n8nUrl = "http://localhost:$localPort"
    Write-Host "   使用URL: $n8nUrl" -ForegroundColor Green
} else {
    $n8nUrl = "http://localhost:5678"
    Write-Host "   使用URL: $n8nUrl (デフォルト)" -ForegroundColor Yellow
}

Write-Host ""

# 設定ファイル1を更新
if (Test-Path $mcpConfigPath1) {
    Write-Host "   cline_mcp_settings.jsonを更新..." -ForegroundColor Cyan
    try {
        $config1 = Get-Content $mcpConfigPath1 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config1.mcpServers.n8n) {
            $oldUrl = $config1.mcpServers.n8n.env.N8N_BASE_URL
            $config1.mcpServers.n8n.env.N8N_BASE_URL = $n8nUrl
            
            Write-Host "      N8N_BASE_URL: $oldUrl → $n8nUrl" -ForegroundColor Gray
            
            # APIキーが設定されているか確認
            if ($config1.mcpServers.n8n.env.N8N_API_KEY -and $config1.mcpServers.n8n.env.N8N_API_KEY -ne "") {
                Write-Host "      ✅ APIキー: 設定済み" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  APIキー: 未設定（後で設定してください）" -ForegroundColor Yellow
            }
            
            $config1 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath1 -Encoding UTF8
            Write-Host "   ✅ cline_mcp_settings.jsonを更新しました" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  n8n設定が見つかりません" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ❌ 更新に失敗: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  cline_mcp_settings.jsonが見つかりません" -ForegroundColor Yellow
}

Write-Host ""

# 設定ファイル2を更新
if (Test-Path $mcpConfigPath2) {
    Write-Host "   mcp.jsonを更新..." -ForegroundColor Cyan
    try {
        $config2 = Get-Content $mcpConfigPath2 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config2.mcpServers.n8n) {
            $oldUrl = $config2.mcpServers.n8n.env.N8N_BASE_URL
            $config2.mcpServers.n8n.env.N8N_BASE_URL = $n8nUrl
            
            Write-Host "      N8N_BASE_URL: $oldUrl → $n8nUrl" -ForegroundColor Gray
            
            # APIキーが設定されているか確認
            if ($config2.mcpServers.n8n.env.N8N_API_KEY -and $config2.mcpServers.n8n.env.N8N_API_KEY -ne "") {
                Write-Host "      ✅ APIキー: 設定済み" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  APIキー: 未設定（後で設定してください）" -ForegroundColor Yellow
            }
            
            $config2 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath2 -Encoding UTF8
            Write-Host "   ✅ mcp.jsonを更新しました" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  n8n設定が見つかりません" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ❌ 更新に失敗: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  mcp.jsonが見つかりません" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "║     ✅ 設定を更新しました！                                      ║" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 次のステップ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ✅ n8nサーバー: $n8nUrl" -ForegroundColor White
Write-Host "   （別ウィンドウで起動中です）" -ForegroundColor Gray
Write-Host ""
Write-Host "2. n8nのWeb UIでAPIキーを作成してください" -ForegroundColor White
Write-Host "   URL: $n8nUrl" -ForegroundColor Cyan
Write-Host "   Settings → API → Create API Key" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 作成したAPIキーを設定ファイルに追加してください" -ForegroundColor White
Write-Host "   または fix_n8n_api_key.ps1 を実行してください" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Cursorを再起動してMCP設定を反映してください" -ForegroundColor White
Write-Host ""