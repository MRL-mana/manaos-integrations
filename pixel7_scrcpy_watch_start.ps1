param(
    [switch]$RemoteOnly,
    [switch]$Portrait,
    [switch]$Landscape,
    [int]$RetryDelaySeconds = 5,
    [int]$MaxDelaySeconds = 60,
    [int]$QuickFailSeconds = 10,
    [double]$BackoffFactor = 2.0,
    [int]$MaxRestarts = 0,
    [switch]$KillExisting,
    [switch]$TurnScreenOff,
    [switch]$Hidden
)

$ErrorActionPreference = 'Stop'

$pidFile = Join-Path $PSScriptRoot '.pixel7_scrcpy_watch.pid'

# 既に動作中なら何もしない
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

$watchScript = Join-Path $PSScriptRoot 'pixel7_scrcpy_watch.ps1'
if (-not (Test-Path $watchScript)) {
    Write-Host ("not found: {0}" -f $watchScript) -ForegroundColor Red
    exit 2
}

$psArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $watchScript
)
if ($RemoteOnly) { $psArgs += '-RemoteOnly' }
if ($Portrait) { $psArgs += '-Portrait' }
if ($Landscape) { $psArgs += '-Landscape' }
if ($KillExisting) { $psArgs += '-KillExisting' }
if ($TurnScreenOff) { $psArgs += '-TurnScreenOff' }
if ($RetryDelaySeconds -gt 0) { $psArgs += @('-RetryDelaySeconds', "$RetryDelaySeconds") }
if ($MaxDelaySeconds -gt 0) { $psArgs += @('-MaxDelaySeconds', "$MaxDelaySeconds") }
if ($QuickFailSeconds -gt 0) { $psArgs += @('-QuickFailSeconds', "$QuickFailSeconds") }
if ($BackoffFactor -gt 0) { $psArgs += @('-BackoffFactor', "$BackoffFactor") }
if ($MaxRestarts -gt 0) { $psArgs += @('-MaxRestarts', "$MaxRestarts") }

$psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
if (-not $psExe) { $psExe = 'powershell' }

$sp = @{
    FilePath     = $psExe
    ArgumentList = $psArgs
    PassThru     = $true
}

if ($Hidden) {
    $sp.WindowStyle = 'Hidden'
}

$p = Start-Process @sp
Write-Host ("started (PID={0})" -f $p.Id) -ForegroundColor Green
