# ManaOS統合MCPサーバーをすべてCursorのMCP設定に追加するスクリプト

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ManaOS統合MCPサーバー Cursor設定追加" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"
$mcpConfigDir = Split-Path $mcpConfigPath -Parent

# ディレクトリが存在しない場合は作成
if (-not (Test-Path $mcpConfigDir)) {
    Write-Host "[1] .cursorディレクトリを作成..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $mcpConfigDir -Force | Out-Null
    Write-Host "   [OK] ディレクトリを作成しました" -ForegroundColor Green
}

# 既存の設定を読み込む
Write-Host "[2] MCP設定ファイルを読み込み..." -ForegroundColor Yellow
if (Test-Path $mcpConfigPath) {
    try {
        $jsonContent = Get-Content $mcpConfigPath -Raw -Encoding UTF8
        $config = $jsonContent | ConvertFrom-Json
        Write-Host "   [OK] 既存の設定を読み込みました" -ForegroundColor Green
    } catch {
        Write-Host "   [警告] 設定ファイルの読み込みに失敗。新規作成します..." -ForegroundColor Yellow
        $config = @{
            mcpServers = @{}
        }
    }
} else {
    Write-Host "   [新規] 設定ファイルが存在しないため、新規作成します" -ForegroundColor Yellow
    $config = @{
        mcpServers = @{}
    }
}

# mcpServersプロパティが存在しない場合は作成
if (-not $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{} -Force
}

$projectPath = "C:\Users\mana4\Desktop\manaos_integrations"

# 追加するMCPサーバーの設定
$mcpServers = @{
    "unified-api" = @{
        command = "python"
        args = @("-m", "unified_api_mcp_server.server")
        env = @{
            MANAOS_INTEGRATION_API_URL = "http://localhost:9500"
        }
        cwd = $projectPath
    }
    "step-deep-research" = @{
        command = "python"
        args = @("-m", "step_deep_research_mcp_server.server")
        env = @{
            STEP_DEEP_RESEARCH_URL = "http://localhost:5121"
        }
        cwd = $projectPath
    }
    "gallery-api" = @{
        command = "python"
        args = @("-m", "gallery_api_mcp_server.server")
        env = @{
            GALLERY_API_URL = "http://localhost:5559"
        }
        cwd = $projectPath
    }
    "system-status" = @{
        command = "python"
        args = @("-m", "system_status_mcp_server.server")
        env = @{
            SYSTEM_STATUS_URL = "http://localhost:5112"
        }
        cwd = $projectPath
    }
    "ssot-api" = @{
        command = "python"
        args = @("-m", "ssot_mcp_server.server")
        env = @{
            SSOT_API_URL = "http://localhost:5120"
        }
        cwd = $projectPath
    }
    "service-monitor" = @{
        command = "python"
        args = @("-m", "service_monitor_mcp_server.server")
        env = @{
            SERVICE_MONITOR_URL = "http://localhost:5111"
        }
        cwd = $projectPath
    }
    "web-voice" = @{
        command = "python"
        args = @("-m", "web_voice_mcp_server.server")
        env = @{
            WEB_VOICE_API_URL = "http://localhost:5115"
        }
        cwd = $projectPath
    }
    "portal-integration" = @{
        command = "python"
        args = @("-m", "portal_integration_mcp_server.server")
        env = @{
            PORTAL_API_URL = "http://localhost:5108"
        }
        cwd = $projectPath
    }
    "slack-integration" = @{
        command = "python"
        args = @("-m", "slack_integration_mcp_server.server")
        env = @{
            SLACK_API_URL = "http://localhost:5114"
        }
        cwd = $projectPath
    }
    "portal-voice-integration" = @{
        command = "python"
        args = @("-m", "portal_voice_integration_mcp_server.server")
        env = @{
            PORTAL_VOICE_API_URL = "http://localhost:5116"
        }
        cwd = $projectPath
    }
}

# MCPサーバーを追加
Write-Host "[3] MCPサーバーを追加..." -ForegroundColor Yellow
$addedCount = 0
$updatedCount = 0

foreach ($serverName in $mcpServers.Keys) {
    $serverConfig = $mcpServers[$serverName]
    
    # PSCustomObjectに変換
    $serverObj = [PSCustomObject]@{
        command = $serverConfig.command
        args = $serverConfig.args
        env = [PSCustomObject]$serverConfig.env
        cwd = $serverConfig.cwd
    }
    
    if ($config.mcpServers.PSObject.Properties.Name -contains $serverName) {
        $config.mcpServers.$serverName = $serverObj
        Write-Host "   [更新] $serverName" -ForegroundColor Cyan
        $updatedCount++
    } else {
        $config.mcpServers | Add-Member -MemberType NoteProperty -Name $serverName -Value $serverObj -Force
        Write-Host "   [追加] $serverName" -ForegroundColor Green
        $addedCount++
    }
}

Write-Host ""
Write-Host "   追加: $addedCount 個" -ForegroundColor Green
Write-Host "   更新: $updatedCount 個" -ForegroundColor Cyan
Write-Host "   合計: $($config.mcpServers.PSObject.Properties.Count) 個のMCPサーバー" -ForegroundColor Yellow

# JSONに変換して保存
Write-Host ""
Write-Host "[4] 設定ファイルを保存..." -ForegroundColor Yellow
try {
    $json = $config | ConvertTo-Json -Depth 10
    $json | Set-Content $mcpConfigPath -Encoding UTF8
    Write-Host "   [OK] 設定ファイルを保存しました" -ForegroundColor Green
    Write-Host "   パス: $mcpConfigPath" -ForegroundColor Gray
} catch {
    Write-Host "   [NG] 設定ファイルの保存に失敗しました" -ForegroundColor Red
    Write-Host "   エラー: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "完了！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動してください" -ForegroundColor White
Write-Host "2. MCPサーバーが利用可能か確認してください" -ForegroundColor White
Write-Host "3. 各APIサービスが起動していることを確認してください" -ForegroundColor White
Write-Host ""
Write-Host "[確認方法]" -ForegroundColor Cyan
Write-Host "docker-compose -f docker-compose.manaos-services.yml ps" -ForegroundColor Gray
Write-Host ""
