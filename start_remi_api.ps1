# Remi API Auto-Start Script
# Registered in Task Scheduler to start on logon
# Waits for network, then launches local_remi_api.py

$ErrorActionPreference = "SilentlyContinue"
$LOG = "$PSScriptRoot\logs\remi_api_autostart.log"
$API_SCRIPT = "$PSScriptRoot\local_remi_api.py"
$PORT = 5050
$DESKTOP_DIR = Split-Path $PSScriptRoot -Parent
$VENV_PY = Join-Path $DESKTOP_DIR ".venv\Scripts\python.exe"

$STDOUT_LOG = "$PSScriptRoot\logs\remi_api_stdout.log"
$STDERR_LOG = "$PSScriptRoot\logs\remi_api_stderr.log"

if (Test-Path $VENV_PY) {
    $PYTHON_EXE = $VENV_PY
} else {
    $PYTHON_EXE = "python"
}

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -Append -FilePath $LOG -Encoding utf8
}

function Get-RemiToken {
    if ($env:REMI_API_TOKEN -and $env:REMI_API_TOKEN.Trim().Length -gt 0) {
        return $env:REMI_API_TOKEN.Trim()
    }

    $envFile = Join-Path $PSScriptRoot ".env"
    if (Test-Path $envFile) {
        try {
            $line = Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*REMI_API_TOKEN\s*=' } | Select-Object -First 1
            if ($line) {
                $val = ($line -split '=', 2)[1]
                if ($val) { return $val.Trim() }
            }
        } catch {
            # ignore
        }
    }

    return "remi-pixel7-2026"
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
    $pid = $($existing.OwningProcess | Select-Object -First 1)
    Write-Log "Port $PORT already in use (PID: $pid). Checking health..."

    $token = Get-RemiToken
    try {
        $headers = @{ Authorization = "Bearer $token" }
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$PORT/health" -Headers $headers -TimeoutSec 5
        Write-Log "Existing service health OK: v$($health.version). Skipping start."
        exit 0
    } catch {
        Write-Log "Existing listener health check failed; restarting. Error: $($_.Exception.Message)"
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } catch {
            Write-Log "Failed to stop PID ${pid}: $($_.Exception.Message)"
        }
    }
}

# Set token
$env:REMI_API_TOKEN = Get-RemiToken
Write-Log "Using REMI_API_TOKEN (length=$($env:REMI_API_TOKEN.Length))"

# Start API
Write-Log "Starting local_remi_api.py..."
$startParams = @{
    FilePath = $PYTHON_EXE
    ArgumentList = $API_SCRIPT
    WindowStyle = 'Hidden'
    PassThru = $true
    WorkingDirectory = $PSScriptRoot
    RedirectStandardOutput = $STDOUT_LOG
    RedirectStandardError = $STDERR_LOG
}
$proc = Start-Process @startParams
Write-Log "Started PID: $($proc.Id)"

# Verify
Start-Sleep -Seconds 5
try {
    $headers = @{ Authorization = "Bearer $($env:REMI_API_TOKEN)" }
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$PORT/health" -Headers $headers -TimeoutSec 5
    Write-Log "Health OK: v$($health.version)"
} catch {
    Write-Log "Health check failed: $($_.Exception.Message)"
}

Write-Log "Auto-start complete"
