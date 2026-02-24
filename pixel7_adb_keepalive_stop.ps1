$ErrorActionPreference = 'Stop'

$pidFile = Join-Path $PSScriptRoot '.pixel7_adb_keepalive.pid'
if (-not (Test-Path $pidFile)) {
    Write-Host 'PID file not found (already stopped?)' -ForegroundColor Yellow
    exit 0
}

$pidText = (Get-Content $pidFile -Raw).Trim()
try { $keepalivePid = [int]$pidText } catch { $keepalivePid = 0 }

if ($keepalivePid -le 0) {
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host 'Invalid PID file, removed.' -ForegroundColor Yellow
    exit 0
}

$p = Get-Process -Id $keepalivePid -ErrorAction SilentlyContinue
if (-not $p) {
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host 'Process not found, removed PID file.' -ForegroundColor Yellow
    exit 0
}

Stop-Process -Id $keepalivePid -Force
Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
Write-Host ('Stopped keepalive (PID={0})' -f $keepalivePid) -ForegroundColor Green
