param(
    [switch]$Force,
    [switch]$KeepStatus
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_edge_watch.pid'
$statusFile = Join-Path $root '.pixel7_edge_watch.status.json'

if (-not (Test-Path $pidFile)) {
    Write-Host 'not running (no pidfile)' -ForegroundColor Yellow
    if (-not $KeepStatus -and (Test-Path $statusFile)) { Remove-Item -Force $statusFile -ErrorAction SilentlyContinue }
    exit 0
}

$pidText = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
if (-not ($pidText -match '^\d+$')) {
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
    Write-Host 'pidfile invalid; removed' -ForegroundColor Yellow
    exit 0
}

$pidValue = [int]$pidText
$p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($p) {
    try {
        Stop-Process -Id $pidValue -Force:$Force -ErrorAction Stop
        Write-Host ("stopped (PID={0})" -f $pidValue) -ForegroundColor Green
    } catch {
        Write-Host ("failed to stop (PID={0}): {1}" -f $pidValue, $_.Exception.Message) -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ("not running (PID {0} not found)" -f $pidValue) -ForegroundColor Yellow
}

Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
if (-not $KeepStatus -and (Test-Path $statusFile)) { Remove-Item -Force $statusFile -ErrorAction SilentlyContinue }

exit 0
