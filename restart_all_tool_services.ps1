# Restart All Tool Services Script
# Restart Tool Server and ComfyUI services

param(
    [switch]$ToolServerOnly,
    [switch]$ComfyUIOnly
)

Write-Host "=== Restart All Tool Services ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Restart Tool Server
if (-not $ComfyUIOnly) {
    Write-Host "[1/2] Restarting Tool Server..." -ForegroundColor Yellow

    # Check if Tool Server is running
    $portCheck = Get-NetTCPConnection -LocalPort 9503 -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "  [INFO] Stopping Tool Server..." -ForegroundColor Gray
        try {
            # Find Python process running Tool Server
            $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
                $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
                $cmdLine -and ($cmdLine -like "*tool_server*main.py*" -or $cmdLine -like "*main.py*")
            }

            if ($processes) {
                foreach ($proc in $processes) {
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }
                Write-Host "  [OK] Tool Server stopped" -ForegroundColor Green
                Start-Sleep -Seconds 2
            }
        } catch {
            Write-Host "  [WARNING] Could not stop Tool Server: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [INFO] Tool Server is not running" -ForegroundColor Gray
    }

    # Start Tool Server
    Write-Host "  [INFO] Starting Tool Server..." -ForegroundColor Gray
    $toolServerScript = Join-Path $scriptDir "START_TOOL_SERVER_HOST.ps1"
    if (Test-Path $toolServerScript) {
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$toolServerScript`"" -WindowStyle Minimized
        Write-Host "  [OK] Tool Server starting..." -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Tool Server script not found: $toolServerScript" -ForegroundColor Red
    }
    Write-Host ""
}

# Restart ComfyUI
if (-not $ToolServerOnly) {
    Write-Host "[2/2] Restarting ComfyUI..." -ForegroundColor Yellow

    # Check if ComfyUI is running
    $portCheck = Get-NetTCPConnection -LocalPort 8188 -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "  [INFO] Stopping ComfyUI..." -ForegroundColor Gray
        try {
            # Find Python process running ComfyUI
            $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
                $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
                $cmdLine -and ($cmdLine -like "*ComfyUI*main.py*" -or ($cmdLine -like "*main.py*" -and $cmdLine -like "*8188*"))
            }

            if ($processes) {
                foreach ($proc in $processes) {
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }
                Write-Host "  [OK] ComfyUI stopped" -ForegroundColor Green
                Start-Sleep -Seconds 2
            }
        } catch {
            Write-Host "  [WARNING] Could not stop ComfyUI: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [INFO] ComfyUI is not running" -ForegroundColor Gray
    }

    # Start ComfyUI
    Write-Host "  [INFO] Starting ComfyUI..." -ForegroundColor Gray
    $comfyUIScript = Join-Path $scriptDir "start_comfyui_svi.ps1"
    if (Test-Path $comfyUIScript) {
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$comfyUIScript`" -Background" -WindowStyle Minimized
        Write-Host "  [OK] ComfyUI starting..." -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] ComfyUI script not found: $comfyUIScript" -ForegroundColor Red
    }
    Write-Host ""
}

# Wait and check status
Write-Host "[INFO] Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "=== Service Status ===" -ForegroundColor Cyan
Write-Host ""

# Check Tool Server
if (-not $ComfyUIOnly) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9503/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "[OK] Tool Server: Running" -ForegroundColor Green
    } catch {
        Write-Host "[NG] Tool Server: Not responding" -ForegroundColor Red
    }
}

# Check ComfyUI
if (-not $ToolServerOnly) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8188" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "[OK] ComfyUI: Running" -ForegroundColor Green
    } catch {
        Write-Host "[NG] ComfyUI: Not responding" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[OK] Restart process completed" -ForegroundColor Green
Write-Host ""
Write-Host "To check detailed status:" -ForegroundColor Cyan
Write-Host "  .\check_all_services_status.ps1" -ForegroundColor Gray
