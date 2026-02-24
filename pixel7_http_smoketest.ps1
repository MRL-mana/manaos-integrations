param(
    [int]$TimeoutSec = 5,
    [switch]$TryOpenOpenWebUI
)

$ErrorActionPreference = 'Stop'

$httpCtl = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$autoCtl = Join-Path $PSScriptRoot 'pixel7_control_auto.ps1'

if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }

Write-Host '=== Pixel7 HTTP Smoke Test ===' -ForegroundColor Cyan

Write-Host '\n[1] health (/health)' -ForegroundColor Gray
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action Health -TimeoutSec $TimeoutSec | Out-Host
} catch {
    Write-Host ("NG: health failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
}

Write-Host '\n[2] status (/api/status) requires PIXEL7_API_TOKEN' -ForegroundColor Gray
$tokenFile = Join-Path $PSScriptRoot '.pixel7_api_token.txt'
if (-not $env:PIXEL7_API_TOKEN -and -not (Test-Path $tokenFile)) {
    Write-Host 'SKIP: PIXEL7_API_TOKEN not set (and token file not found)' -ForegroundColor Yellow
} else {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action Status -TimeoutSec $TimeoutSec | Out-Host
    } catch {
        Write-Host ("NG: status failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }

    Write-Host '\n[2b] macro commands (/api/macro/commands)' -ForegroundColor Gray
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action MacroCommands -TimeoutSec $TimeoutSec | Out-Host
    } catch {
        Write-Host ("NG: macro commands failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host '\n[3] HTTP→ADB fallback action (OpenHttpShortcuts)' -ForegroundColor Gray
if (Test-Path $autoCtl) {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $autoCtl -Action OpenHttpShortcuts -Mode HTTPFirst -TimeoutSec $TimeoutSec | Out-Host
    } catch {
        Write-Host ("NG: fallback action failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
} else {
    Write-Host 'SKIP: pixel7_control_auto.ps1 not found' -ForegroundColor Yellow
}

if ($TryOpenOpenWebUI) {
    Write-Host '\n[4] HTTP→ADB fallback action (OpenOpenWebUI)' -ForegroundColor Gray
    if (Test-Path $autoCtl) {
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $autoCtl -Action OpenOpenWebUI -Mode HTTPFirst -TimeoutSec $TimeoutSec | Out-Host
        } catch {
            Write-Host ("NG: OpenOpenWebUI failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
        }
    }
}

Write-Host '\nOK' -ForegroundColor Green
