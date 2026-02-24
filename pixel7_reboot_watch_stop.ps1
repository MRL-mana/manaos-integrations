param(
    [switch]$KeepStatus
)

$ErrorActionPreference = 'Stop'

$pidFile = Join-Path $PSScriptRoot '.pixel7_reboot_watch.pid'
$statusFile = Join-Path $PSScriptRoot '.pixel7_reboot_watch.status.json'

if (Test-Path $pidFile) {
    try {
        $watchPid = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
        if ($watchPid -match '^\d+$') {
            Stop-Process -Id ([int]$watchPid) -Force -ErrorAction SilentlyContinue
        }
    } catch {}

    try { Remove-Item $pidFile -Force -ErrorAction SilentlyContinue } catch {}
}

if (-not $KeepStatus) {
    try { Remove-Item $statusFile -Force -ErrorAction SilentlyContinue } catch {}
}

Write-Host 'OK' -ForegroundColor Green
