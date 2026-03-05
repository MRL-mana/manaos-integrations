# =============================================================================
# ManaOS: start_all_services.ps1
# Tier 0 → Tier 1 → Optional の順に全サービス起動
# Usage: powershell scripts\start_all_services.ps1
# =============================================================================

$base = "C:\Users\mana4\Desktop\manaos_integrations"
$py   = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"

Set-Location $base
Write-Host "Starting ManaOS services from: $base" -ForegroundColor Cyan

function Start-Service-If-Not-Running {
    param([string]$Label, [string]$Script, [string]$ModuleOrFile = "file", [int]$Port = 0)

    # ポート指定ありの場合は起動済みチェック
    if ($Port -gt 0) {
        $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listening) {
            Write-Host "  [SKIP] $Label (port $Port already listening)" -ForegroundColor Yellow
            return
        }
    }

    if ($ModuleOrFile -eq "module") {
        Start-Process $py -ArgumentList "-m", $Script -WorkingDirectory $base -WindowStyle Hidden
    } else {
        Start-Process $py -ArgumentList $Script -WorkingDirectory $base -WindowStyle Hidden
    }
    Write-Host "  [START] $Label" -ForegroundColor Green
    Start-Sleep -Milliseconds 300
}

# ──────────────────────────────────────────────────────────────────────────────
# Tier 0 (根幹)
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "`n[Tier 0] Core services" -ForegroundColor Magenta

# ollama は外部プロセス - 起動済みチェックのみ
if (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "  [SKIP] ollama (port 11434 already listening)" -ForegroundColor Yellow
} else {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "  [START] ollama" -ForegroundColor Green
    Start-Sleep -Seconds 2
}

Start-Service-If-Not-Running "memory (mrl_memory)"       "mrl_memory_integration.py"           -Port 5105
Start-Service-If-Not-Running "llm_routing"               "scripts\misc\manaos_llm_routing_api.py" -Port 5111
Start-Service-If-Not-Running "unified_api"               "unified_api\unified_api_server.py"   -Port 9502

Write-Host "  Waiting for Tier 0 to stabilize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# ──────────────────────────────────────────────────────────────────────────────
# Tier 1 (主要機能)
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "`n[Tier 1] Main services" -ForegroundColor Magenta

Start-Service-If-Not-Running "learning"                  "learning_system_api.py"              -Port 5126
Start-Service-If-Not-Running "personality"               "scripts.misc.personality_system"     -ModuleOrFile "module" -Port 5123
Start-Service-If-Not-Running "autonomy"                  "scripts\misc\autonomy_system.py"     -Port 5124
Start-Service-If-Not-Running "secretary"                 "scripts\misc\secretary_system.py"    -Port 5125
Start-Service-If-Not-Running "trinity"                   "trinity_mcp_server/server.py"        -Port 5146
Start-Service-If-Not-Running "intent_router"             "scripts\misc\intent_router.py"       -Port 5100
Start-Service-If-Not-Running "task_queue"                "scripts\misc\task_queue_system.py"   -Port 5104

Write-Host "  Waiting for Tier 1 to stabilize..." -ForegroundColor Gray
Start-Sleep -Seconds 2

# ──────────────────────────────────────────────────────────────────────────────
# Optional (Tier 2)
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "`n[Tier 2] Optional services" -ForegroundColor Magenta

Start-Service-If-Not-Running "windows_automation"        "windows_automation_mcp_server\server.py"
Start-Service-If-Not-Running "pixel7_bridge"             "pixel7_api_gateway.py"
Start-Service-If-Not-Running "slack_integration"         "mcp-servers/slack_integration/slack_manaos_service.py"

# ──────────────────────────────────────────────────────────────────────────────
# 完了
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "`nAll services launched. Running blast_radius check in 5s..." -ForegroundColor Cyan
Start-Sleep -Seconds 5
python tools\check_blast_radius.py --live 2>&1 | Select-Object -Last 20
