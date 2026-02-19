# Open WebUI × ManaOS フルスタック起動スクリプト
# 必須: Unified API / Learning / Personality / Autonomy / Secretary / Tool Server
# 任意: Open WebUI (すでに起動済み想定)

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
$ErrorActionPreference = "Continue"

Write-Host "=== Open WebUI × ManaOS Full Start ===" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = "py"
$pythonArgs = "-3.10"

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $conn
}

function Start-PythonService {
    param(
        [string]$Name,
        [int]$Port,
        [string]$ScriptPath,
        [string]$ExtraArgs = ""
    )

    if (Test-PortListening -Port $Port) {
        Write-Host "[OK] $Name already running on :$Port" -ForegroundColor Green
        return
    }

    if (-not (Test-Path $ScriptPath)) {
        Write-Host "[NG] $Name script not found: $ScriptPath" -ForegroundColor Red
        return
    }

    Write-Host "[START] $Name on :$Port" -ForegroundColor Yellow
    $argLine = "$pythonArgs -u `"$ScriptPath`" $ExtraArgs"
    Start-Process -FilePath $pythonExe -ArgumentList $argLine -WorkingDirectory $scriptDir -WindowStyle Minimized
    Start-Sleep -Seconds 2

    if (Test-PortListening -Port $Port) {
        Write-Host "[OK] $Name started" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $Name did not open port yet" -ForegroundColor Yellow
    }
}

function Start-ToolServer {
    $port = 9503
    if (Test-PortListening -Port $port) {
        Write-Host "[OK] Tool Server already running on :$port" -ForegroundColor Green
        return
    }

    $starter = Join-Path $scriptDir "START_TOOL_SERVER_HOST.ps1"
    if (-not (Test-Path $starter)) {
        Write-Host "[NG] Tool Server starter not found: $starter" -ForegroundColor Red
        return
    }

    Write-Host "[START] Tool Server on :$port" -ForegroundColor Yellow
    Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy Bypass -File `"$starter`"" -WorkingDirectory $scriptDir -WindowStyle Minimized
    Start-Sleep -Seconds 3

    if (Test-PortListening -Port $port) {
        Write-Host "[OK] Tool Server started" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Tool Server did not open port yet" -ForegroundColor Yellow
    }
}

# 必須サービス
Start-PythonService -Name "Unified API" -Port 9502 -ScriptPath (Join-Path $scriptDir "unified_api_server.py")
Start-PythonService -Name "Learning System" -Port 5126 -ScriptPath (Join-Path $scriptDir "learning_system_api.py")
Start-PythonService -Name "Personality System" -Port 5123 -ScriptPath (Join-Path $scriptDir "personality_system.py")
Start-PythonService -Name "Autonomy System" -Port 5124 -ScriptPath (Join-Path $scriptDir "autonomy_system.py")
Start-PythonService -Name "Secretary System" -Port 5125 -ScriptPath (Join-Path $scriptDir "secretary_system.py")
Start-ToolServer

# Open WebUI 状態（起動は別経路）
try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:3001" -TimeoutSec 4 | Out-Null
    Write-Host "[OK] Open WebUI running on :3001" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Open WebUI is not reachable on :3001" -ForegroundColor Yellow
}

Write-Host "\n[CHECK] Running setup verifier..." -ForegroundColor Cyan
$checker = Join-Path $scriptDir "setup_openwebui_manaos_complete.py"
if (Test-Path $checker) {
    & $pythonExe $pythonArgs $checker
} else {
    Write-Host "[WARN] setup_openwebui_manaos_complete.py not found" -ForegroundColor Yellow
}

Write-Host "\n=== Full Start Completed ===" -ForegroundColor Cyan
