param(
    [int]$IntervalSeconds = 300,
    [int]$DegradedIntervalSeconds = 60,
    [int]$DegradedAfterFailures = 2,
    [int]$StrongRecoverAfterFailures = 5,
    [int]$StrongRecoverCooldownSec = 600,
    [switch]$EnableRebootTestRecovery,
    [int]$RebootTestAfterFailures = 8,
    [int]$RebootTestCooldownSec = 3600,
    [int]$FailureNotifyCooldownSec = 900,
    [int]$ForcedGatewayRecoverCooldownSec = 300,
    [switch]$AutoRecoverOnFailure,
    [switch]$RemoteOnly,
    [switch]$NotifyOnRecover,
    [string]$PixelHost = "",
    [int]$ApiPort = 0,
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_edge_watch.pid'
$watch = Join-Path $root 'pixel7_edge_watch.ps1'

if (-not (Test-Path $watch)) { throw "not found: $watch" }

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

$argsList = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $watch,
    '-IntervalSeconds', [string]$IntervalSeconds,
    '-DegradedIntervalSeconds', [string]$DegradedIntervalSeconds,
    '-DegradedAfterFailures', [string]$DegradedAfterFailures,
    '-StrongRecoverAfterFailures', [string]$StrongRecoverAfterFailures,
    '-StrongRecoverCooldownSec', [string]$StrongRecoverCooldownSec,
    '-RebootTestAfterFailures', [string]$RebootTestAfterFailures,
    '-RebootTestCooldownSec', [string]$RebootTestCooldownSec,
    '-FailureNotifyCooldownSec', [string]$FailureNotifyCooldownSec,
    '-ForcedGatewayRecoverCooldownSec', [string]$ForcedGatewayRecoverCooldownSec
)
if ($AutoRecoverOnFailure) { $argsList += '-AutoRecoverOnFailure' }
if ($EnableRebootTestRecovery) { $argsList += '-EnableRebootTestRecovery' }
if ($RemoteOnly) { $argsList += '-RemoteOnly' }
if ($NotifyOnRecover) { $argsList += '-NotifyOnRecover' }
if ($PixelHost) { $argsList += @('-PixelHost', $PixelHost) }
if ($ApiPort -gt 0) { $argsList += @('-ApiPort', [string]$ApiPort) }
if ($DeviceSerial) { $argsList += @('-DeviceSerial', $DeviceSerial) }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'pwsh'
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
