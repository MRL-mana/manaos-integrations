# n8n接続問題の解決スクリプト
# リモートサーバー接続問題を診断し、ローカルn8nサーバーへの切り替えを支援

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     n8n接続問題の解決スクリプト                                  ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 設定ファイルのパス
$mcpConfigPath1 = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
$mcpConfigPath2 = "$env:USERPROFILE\.cursor\mcp.json"

Write-Host "[1] 現在の接続状況を確認..." -ForegroundColor Yellow
Write-Host ""

# リモートサーバーの確認
Write-Host "   リモートサーバー (100.93.120.33:5678):" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://100.93.120.33:5678/healthz" -Method GET -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ 接続可能" -ForegroundColor Green
    $useRemote = $true
} catch {
    Write-Host "   ❌ 接続不可: $($_.Exception.Message)" -ForegroundColor Red
    $useRemote = $false
}

Write-Host ""
Write-Host "   ローカルサーバー (localhost:5678):" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   ✅ 接続可能" -ForegroundColor Green
    $useLocal = $true
    $localPort = 5678
} catch {
    Write-Host "   ⚠️  接続不可（ポート5678）" -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5679/healthz" -Method GET -TimeoutSec 2 -ErrorAction Stop
        Write-Host "   ✅ 接続可能（ポート5679）" -ForegroundColor Green
        $useLocal = $true
        $localPort = 5679
    } catch {
        Write-Host "   ❌ 接続不可（ポート5679も）" -ForegroundColor Red
        $useLocal = $false
    }
}

Write-Host ""

# どちらも接続できない場合
if (-not $useRemote -and -not $useLocal) {
    Write-Host "[2] ローカルn8nサーバーを起動しますか？" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   リモートサーバーにもローカルサーバーにも接続できません。" -ForegroundColor Gray
    Write-Host "   ローカルn8nサーバーを起動しますか？" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   選択肢:" -ForegroundColor Cyan
    Write-Host "   1. ローカルn8nサーバーを起動する（推奨）" -ForegroundColor White
    Write-Host "   2. 設定のみ変更して終了（手動でn8nを起動）" -ForegroundColor White
    Write-Host "   3. キャンセル" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "   選択 (1/2/3)"
    
    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "   n8nサーバーを起動します..." -ForegroundColor Yellow
        
        # n8nがインストールされているか確認
        $n8nInstalled = Get-Command n8n -ErrorAction SilentlyContinue
        if (-not $n8nInstalled) {
            Write-Host "   ⚠️  n8nがインストールされていません" -ForegroundColor Yellow
            Write-Host "   インストールスクリプトを実行しますか？ (Y/N)" -ForegroundColor Cyan
            $install = Read-Host
            if ($install -eq "Y" -or $install -eq "y") {
                if (Test-Path "install_n8n_local.ps1") {
                    & ".\install_n8n_local.ps1"
                } else {
                    Write-Host "   ❌ install_n8n_local.ps1が見つかりません" -ForegroundColor Red
                    exit 1
                }
            } else {
                Write-Host "   n8nのインストールをスキップします" -ForegroundColor Yellow
                exit 1
            }
        }
        
        # n8nを起動
        if (Test-Path "start_n8n_local.ps1") {
            Write-Host "   start_n8n_local.ps1を実行します..." -ForegroundColor Gray
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; .\start_n8n_local.ps1" -WindowStyle Normal
            Write-Host "   ✅ n8nサーバーを起動しました" -ForegroundColor Green
            Write-Host "   5秒待機してから接続を確認します..." -ForegroundColor Gray
            Start-Sleep -Seconds 5
            
            # 接続確認
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -Method GET -TimeoutSec 3 -ErrorAction Stop
                Write-Host "   ✅ ローカルn8nサーバーに接続できました" -ForegroundColor Green
                $useLocal = $true
                $localPort = 5678
            } catch {
                Write-Host "   ⚠️  まだ起動中の可能性があります。手動で確認してください" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   ⚠️  start_n8n_local.ps1が見つかりません" -ForegroundColor Yellow
            Write-Host "   手動でn8nを起動してください: n8n start" -ForegroundColor Gray
        }
    } elseif ($choice -eq "2") {
        Write-Host "   設定のみ変更します" -ForegroundColor Yellow
    } else {
        Write-Host "   キャンセルしました" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "[3] MCP設定ファイルを更新..." -ForegroundColor Yellow

# 使用するURLとポートを決定
if ($useLocal) {
    $n8nUrl = "http://localhost:$localPort"
    Write-Host "   ローカルn8nサーバーを使用: $n8nUrl" -ForegroundColor Green
} elseif ($useRemote) {
    $n8nUrl = "http://100.93.120.33:5678"
    Write-Host "   リモートn8nサーバーを使用: $n8nUrl" -ForegroundColor Green
} else {
    $n8nUrl = "http://localhost:5678"
    Write-Host "   デフォルト設定を使用: $n8nUrl" -ForegroundColor Yellow
    Write-Host "   （n8nサーバーを起動してから再度実行してください）" -ForegroundColor Gray
}

Write-Host ""

# 設定ファイル1を更新
if (Test-Path $mcpConfigPath1) {
    Write-Host "   cline_mcp_settings.jsonを更新..." -ForegroundColor Cyan
    try {
        $config1 = Get-Content $mcpConfigPath1 -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($config1.mcpServers.n8n) {
            $config1.mcpServers.n8n.env.N8N_BASE_URL = $n8nUrl
            Write-Host "      N8N_BASE_URLを更新: $n8nUrl" -ForegroundColor Gray
            
            # APIキーが設定されていない場合
            if (-not $config1.mcpServers.n8n.env.N8N_API_KEY -or $config1.mcpServers.n8n.env.N8N_API_KEY -eq "") {
                Write-Host "      ⚠️  APIキーが設定されていません" -ForegroundColor Yellow
                Write-Host "      APIキーを入力してください（Enterでスキップ）:" -ForegroundColor Cyan
                $apiKey = Read-Host "      APIキー"
                if ($apiKey) {
                    $config1.mcpServers.n8n.env.N8N_API_KEY = $apiKey
                    Write-Host "      ✅ APIキーを設定しました" -ForegroundColor Green
                }
            }
            
        } else {
            Write-Host "      ⚠️  n8n設定が見つかりません" -ForegroundColor Yellow
        }
        
        $config1 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath1 -Encoding UTF8
        Write-Host "   ✅ cline_mcp_settings.jsonを更新しました" -ForegroundColor Green
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
            $config2.mcpServers.n8n.env.N8N_BASE_URL = $n8nUrl
            Write-Host "      N8N_BASE_URLを更新: $n8nUrl" -ForegroundColor Gray
            
            # APIキーが設定されていない場合
            if (-not $config2.mcpServers.n8n.env.N8N_API_KEY -or $config2.mcpServers.n8n.env.N8N_API_KEY -eq "") {
                if (-not $apiKey) {
                    Write-Host "      ⚠️  APIキーが設定されていません" -ForegroundColor Yellow
                    Write-Host "      APIキーを入力してください（Enterでスキップ）:" -ForegroundColor Cyan
                    $apiKey = Read-Host "      APIキー"
                }
                if ($apiKey) {
                    $config2.mcpServers.n8n.env.N8N_API_KEY = $apiKey
                    Write-Host "      ✅ APIキーを設定しました" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "      ⚠️  n8n設定が見つかりません" -ForegroundColor Yellow
        }
        
        $config2 | ConvertTo-Json -Depth 10 | Set-Content $mcpConfigPath2 -Encoding UTF8
        Write-Host "   ✅ mcp.jsonを更新しました" -ForegroundColor Green
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
Write-Host "1. Cursorを再起動してMCP設定を反映してください" -ForegroundColor White
Write-Host "2. n8nサーバーが起動していることを確認してください" -ForegroundColor White
if ($useLocal) {
    Write-Host "   URL: $n8nUrl" -ForegroundColor Gray
} else {
    Write-Host "   URL: $n8nUrl" -ForegroundColor Gray
    Write-Host "   （サーバーを起動してから接続してください）" -ForegroundColor Yellow
}
Write-Host "3. n8nのWeb UIでAPIキーを作成してください" -ForegroundColor White
Write-Host "   Settings → API → Create API Key" -ForegroundColor Gray
Write-Host "4. 作成したAPIキーを設定ファイルに追加してください" -ForegroundColor White
Write-Host ""