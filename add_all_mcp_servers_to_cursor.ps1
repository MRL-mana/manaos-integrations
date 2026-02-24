# ManaOS統合MCPサーバーをすべてCursorのMCP設定に追加するスクリプト

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ManaOS統合MCPサーバー Cursor設定追加" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# URL（環境変数で上書き可能）
$unifiedApiPort = if ($env:UNIFIED_API_PORT) { $env:UNIFIED_API_PORT } elseif ($env:PORT) { $env:PORT } else { "9502" }
$galleryPort = if ($env:GALLERY_PORT) { $env:GALLERY_PORT } else { "5559" }
$comfyUiPort = if ($env:COMFYUI_PORT) { $env:COMFYUI_PORT } else { "8188" }
$portalIntegrationPort = if ($env:PORTAL_INTEGRATION_PORT) { $env:PORTAL_INTEGRATION_PORT } else { "5108" }
$stepDeepResearchPort = if ($env:STEP_DEEP_RESEARCH_PORT) { $env:STEP_DEEP_RESEARCH_PORT } else { "5121" }
$systemStatusPort = if ($env:SYSTEM_STATUS_PORT) { $env:SYSTEM_STATUS_PORT } else { "5112" }
$ssotPort = if ($env:FILE_SECRETARY_PORT) { $env:FILE_SECRETARY_PORT } else { "5120" }
$serviceMonitorPort = if ($env:LLM_ROUTING_PORT) { $env:LLM_ROUTING_PORT } else { "5117" }
$webVoicePort = if ($env:WINDOWS_AUTOMATION_PORT) { $env:WINDOWS_AUTOMATION_PORT } else { "5115" }
$slackPort = if ($env:SLACK_INTEGRATION_PORT) { $env:SLACK_INTEGRATION_PORT } else { "5114" }
$portalVoicePort = if ($env:PORTAL_VOICE_INTEGRATION_PORT) { $env:PORTAL_VOICE_INTEGRATION_PORT } else { "5116" }

$unifiedApiBaseUrl = if ($env:MANAOS_INTEGRATION_API_URL) { $env:MANAOS_INTEGRATION_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$unifiedApiPort" }
$galleryApiBaseUrl = if ($env:GALLERY_API_URL) { $env:GALLERY_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$galleryPort" }
$comfyUiBaseUrl = if ($env:COMFYUI_URL) { $env:COMFYUI_URL.TrimEnd('/') } else { "http://127.0.0.1:$comfyUiPort" }
$portalIntegrationBaseUrl = if ($env:PORTAL_INTEGRATION_URL) { $env:PORTAL_INTEGRATION_URL.TrimEnd('/') } else { "http://127.0.0.1:$portalIntegrationPort" }

$stepDeepResearchBaseUrl = if ($env:STEP_DEEP_RESEARCH_URL) { $env:STEP_DEEP_RESEARCH_URL.TrimEnd('/') } else { "http://127.0.0.1:$stepDeepResearchPort" }
$systemStatusBaseUrl = if ($env:SYSTEM_STATUS_URL) { $env:SYSTEM_STATUS_URL.TrimEnd('/') } else { "http://127.0.0.1:$systemStatusPort" }
$ssotApiBaseUrl = if ($env:SSOT_API_URL) { $env:SSOT_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$ssotPort" }
$serviceMonitorBaseUrl = if ($env:SERVICE_MONITOR_URL) { $env:SERVICE_MONITOR_URL.TrimEnd('/') } else { "http://127.0.0.1:$serviceMonitorPort" }
$webVoiceApiBaseUrl = if ($env:WEB_VOICE_API_URL) { $env:WEB_VOICE_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$webVoicePort" }
$slackApiBaseUrl = if ($env:SLACK_API_URL) { $env:SLACK_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$slackPort" }
$portalVoiceApiBaseUrl = if ($env:PORTAL_VOICE_API_URL) { $env:PORTAL_VOICE_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$portalVoicePort" }

# 互換性: PORTAL_API_URL が設定されている環境も吸収
$portalApiBaseUrl = if ($env:PORTAL_API_URL) { $env:PORTAL_API_URL.TrimEnd('/') } else { $portalIntegrationBaseUrl }

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

# スクリプトの親ディレクトリ＝プロジェクトルート（ポータブル）
$projectPath = if ($PSScriptRoot) { (Resolve-Path $PSScriptRoot).Path } else { (Get-Location).Path }

# 追加するMCPサーバーの設定
$mcpServers = @{
    "unified-api"              = @{
        command = "python"
        args    = @("-m", "unified_api_mcp_server.server")
        env     = @{
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
        }
        cwd     = $projectPath
    }
    "step-deep-research"       = @{
        command = "python"
        args    = @("-m", "step_deep_research_mcp_server.server")
        env     = @{
            STEP_DEEP_RESEARCH_URL = $stepDeepResearchBaseUrl
        }
        cwd     = $projectPath
    }
    "gallery-api"              = @{
        command = "python"
        args    = @("-m", "gallery_api_mcp_server.server")
        env     = @{
            GALLERY_API_URL = $galleryApiBaseUrl
        }
        cwd     = $projectPath
    }
    "system-status"            = @{
        command = "python"
        args    = @("-m", "system_status_mcp_server.server")
        env     = @{
            SYSTEM_STATUS_URL = $systemStatusBaseUrl
        }
        cwd     = $projectPath
    }
    "ssot-api"                 = @{
        command = "python"
        args    = @("-m", "ssot_mcp_server.server")
        env     = @{
            SSOT_API_URL = $ssotApiBaseUrl
        }
        cwd     = $projectPath
    }
    "service-monitor"          = @{
        command = "python"
        args    = @("-m", "service_monitor_mcp_server.server")
        env     = @{
            SERVICE_MONITOR_URL = $serviceMonitorBaseUrl
        }
        cwd     = $projectPath
    }
    "web-voice"                = @{
        command = "python"
        args    = @("-m", "web_voice_mcp_server.server")
        env     = @{
            WEB_VOICE_API_URL = $webVoiceApiBaseUrl
        }
        cwd     = $projectPath
    }
    "portal-integration"       = @{
        command = "python"
        args    = @("-m", "portal_integration_mcp_server.server")
        env     = @{
            PORTAL_API_URL = $portalApiBaseUrl
        }
        cwd     = $projectPath
    }
    "slack-integration"        = @{
        command = "python"
        args    = @("-m", "slack_integration_mcp_server.server")
        env     = @{
            SLACK_API_URL = $slackApiBaseUrl
        }
        cwd     = $projectPath
    }
    "portal-voice-integration" = @{
        command = "python"
        args    = @("-m", "portal_voice_integration_mcp_server.server")
        env     = @{
            PORTAL_VOICE_API_URL = $portalVoiceApiBaseUrl
        }
        cwd     = $projectPath
    }
    "ltx2"                     = @{
        command = "python"
        args    = @("-m", "ltx2_mcp_server.server")
        env     = @{
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
        }
        cwd     = $projectPath
    }
    "phase1"                   = @{
        command = "python"
        args    = @("-m", "phase1_mcp_server.server")
        env     = @{}
        cwd     = $projectPath
    }
    "manaos-media"             = @{
        command = "python"
        args    = @("-m", "manaos_unified_mcp_server.server")
        env     = @{
            MCP_DOMAIN                 = "media"
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
            COMFYUI_URL                = $comfyUiBaseUrl
        }
        cwd     = $projectPath
    }
    "manaos-productivity"      = @{
        command = "python"
        args    = @("-m", "manaos_unified_mcp_server.server")
        env     = @{
            MCP_DOMAIN                 = "productivity"
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
        }
        cwd     = $projectPath
    }
    "manaos-ai"                = @{
        command = "python"
        args    = @("-m", "manaos_unified_mcp_server.server")
        env     = @{
            MCP_DOMAIN                 = "ai"
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
        }
        cwd     = $projectPath
    }
    "manaos-devices"           = @{
        command = "python"
        args    = @("-m", "manaos_unified_mcp_server.server")
        env     = @{
            MCP_DOMAIN                 = "devices"
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
            PORTAL_INTEGRATION_URL     = $portalIntegrationBaseUrl
        }
        cwd     = $projectPath
    }
    "manaos-moltbot"           = @{
        command = "python"
        args    = @("-m", "manaos_unified_mcp_server.server")
        env     = @{
            MCP_DOMAIN                 = "moltbot"
            MANAOS_INTEGRATION_API_URL = $unifiedApiBaseUrl
        }
        cwd     = $projectPath
    }

    "manaos-pico-hid"          = @{
        command = "python"
        args    = @("-m", "pico_hid_mcp_server")
        env     = @{
            # 5116 は Portal Voice Integration と衝突するため避ける
            PICO_HID_MCP_HEALTH_PORT = "5136"
        }
        cwd     = $projectPath
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
        args    = $serverConfig.args
        env     = [PSCustomObject]$serverConfig.env
        cwd     = $serverConfig.cwd
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
