param(
    [switch]$RemoteOnly,
    [int]$IntervalSeconds = 30,
    [switch]$RestartAdbOnStart,
    [switch]$Hidden
)

$ErrorActionPreference = 'Stop'

$pidFile = Join-Path $PSScriptRoot '.pixel7_reboot_watch.pid'
if (Test-Path $pidFile) {
    try {
        $watchPid = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
        if ($watchPid -match '^\d+$') {
            $p = Get-Process -Id ([int]$watchPid) -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host ("already running (PID={0})" -f $watchPid) -ForegroundColor Green
                exit 0
            }
        }
    } catch {}
}

$watchScript = Join-Path $PSScriptRoot 'pixel7_reboot_watch.ps1'
if (-not (Test-Path $watchScript)) {
    Write-Host ("not found: {0}" -f $watchScript) -ForegroundColor Red
    exit 2
}

$psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
if (-not $psExe) { $psExe = 'powershell' }

$psArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $watchScript,
    '-IntervalSeconds', "$IntervalSeconds"
)
if ($RemoteOnly) { $psArgs += '-RemoteOnly' }
if ($RestartAdbOnStart) { $psArgs += '-RestartAdbOnStart' }

$sp = @{
    FilePath     = $psExe
    ArgumentList = $psArgs
    PassThru     = $true
}
if ($Hidden) { $sp.WindowStyle = 'Hidden' }

$p = Start-Process @sp
Write-Host ("started (PID={0})" -f $p.Id) -ForegroundColor Green
