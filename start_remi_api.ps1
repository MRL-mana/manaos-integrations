# Remi API Auto-Start Script
# Registered in Task Scheduler to start on logon
# Waits for network, then launches local_remi_api.py

$ErrorActionPreference = "SilentlyContinue"
$LOG = "$PSScriptRoot\logs\remi_api_autostart.log"
$API_SCRIPT = "$PSScriptRoot\local_remi_api.py"
$PORT = 5050

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -Append -FilePath $LOG -Encoding utf8
}

# Ensure log dir
if (-not (Test-Path "$PSScriptRoot\logs")) { New-Item -ItemType Directory -Path "$PSScriptRoot\logs" -Force | Out-Null }

Write-Log "=== Remi API Auto-Start ==="

# Wait for network (Tailscale)
$retries = 0
while ($retries -lt 30) {
    $ts = tailscale status 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Tailscale is up"
        break
    }
    $retries++
    Write-Log "Waiting for Tailscale... ($retries/30)"
    Start-Sleep -Seconds 5
}

# Check if already running
$existing = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Log "Port $PORT already in use (PID: $($existing.OwningProcess | Select-Object -First 1)). Skipping."
    exit 0
}

# Set token
$env:REMI_API_TOKEN = "remi-pixel7-2026"

# Start API
Write-Log "Starting local_remi_api.py..."
$proc = Start-Process -FilePath "python" -ArgumentList $API_SCRIPT -WindowStyle Hidden -PassThru -WorkingDirectory $PSScriptRoot
Write-Log "Started PID: $($proc.Id)"

# Verify
Start-Sleep -Seconds 5
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$PORT/health" -TimeoutSec 5
    Write-Log "Health OK: v$($health.version)"
} catch {
    Write-Log "Health check failed: $($_.Exception.Message)"
}

Write-Log "Auto-start complete"
