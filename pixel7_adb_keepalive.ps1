param(
    [int]$IntervalSeconds = 60,
    [switch]$RestartAdbOnStart,
    [switch]$RemoteOnly
)

$ErrorActionPreference = 'Stop'

if ($IntervalSeconds -lt 10) { $IntervalSeconds = 10 }
if ($IntervalSeconds -gt 600) { $IntervalSeconds = 600 }

$pidFile = Join-Path $PSScriptRoot '.pixel7_adb_keepalive.pid'
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir ('pixel7_adb_keepalive_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

function Write-Log([string]$msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $msg"
    $line | Out-Host
    Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
}

Set-Content -Path $pidFile -Value $PID -Encoding ASCII
Write-Log "=== Pixel7 ADB Keepalive started (PID=$PID, interval=${IntervalSeconds}s) ==="

$recover = Join-Path $PSScriptRoot 'pixel7_adb_recover_wireless.ps1'
if (-not (Test-Path $recover)) {
    Write-Log "ERROR: not found: $recover"
    exit 2
}

$first = $true
while ($true) {
    try {
        if ($first -and $RestartAdbOnStart) {
            if ($RemoteOnly) {
                & $recover -RestartAdb -RemoteOnly | Out-Null
            } else {
                & $recover -RestartAdb | Out-Null
            }
        } else {
            if ($RemoteOnly) {
                & $recover -RemoteOnly | Out-Null
            } else {
                & $recover | Out-Null
            }
        }
        $first = $false
        Write-Log 'tick ok'
    } catch {
        Write-Log ("tick error: {0}" -f $_.Exception.Message)
        try {
            if ($RemoteOnly) {
                & $recover -RestartAdb -RemoteOnly | Out-Null
            } else {
                & $recover -RestartAdb | Out-Null
            }
            Write-Log 'recovered with RestartAdb'
        } catch {
            Write-Log ("recover failed: {0}" -f $_.Exception.Message)
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
