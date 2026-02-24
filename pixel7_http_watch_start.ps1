param(
    [int]$IntervalSeconds = 15,
    [int]$TimeoutSec = 3,
    [int]$FailThreshold = 3,
    [switch]$AttemptRecovery,
    [switch]$RemoteOnly
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_http_watch.pid'

if (Test-Path $pidFile) {
    $existing = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
    if ($existing -match '^\d+$') {
        $p = Get-Process -Id ([int]$existing) -ErrorAction SilentlyContinue
        if ($p) {
            Write-Host ("already running (PID={0})" -f $existing) -ForegroundColor Yellow
            exit 0
        }
    }
}

$watch = Join-Path $root 'pixel7_http_watch.ps1'
if (-not (Test-Path $watch)) { throw "not found: $watch" }

$argsList = @(
    '-NoProfile','-ExecutionPolicy','Bypass','-File', $watch,
    '-IntervalSeconds', [string]$IntervalSeconds,
    '-TimeoutSec', [string]$TimeoutSec,
    '-FailThreshold', [string]$FailThreshold
)
if ($AttemptRecovery) { $argsList += '-AttemptRecovery' }
if ($RemoteOnly) { $argsList += '-RemoteOnly' }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'powershell'
$psi.Arguments = ($argsList -join ' ')
$psi.WorkingDirectory = $root
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $true

$p = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Milliseconds 300

if ($p -and -not $p.HasExited) {
    Write-Host ("started (PID={0})" -f $p.Id) -ForegroundColor Green
    exit 0
}

Write-Host 'failed to start' -ForegroundColor Red
exit 1
