param(
    [switch]$RemoteOnly,
    [switch]$BootstrapGateway,
    [switch]$AttemptRecovery,
    [switch]$ContinueOnGatewayFailure,
    [int]$WatchIntervalSeconds = 15,
    [int]$WatchFailThreshold = 3,
    [int]$WatchTimeoutSec = 3,
    [int]$GatewayWaitListenSec = 120
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
if (-not $psExe) { $psExe = 'powershell' }

function Invoke-Script {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptName,
        [string[]]$Args = @()
    )

    $scriptPath = Join-Path $root $ScriptName
    if (-not (Test-Path $scriptPath)) {
        throw "not found: $scriptPath"
    }

    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath) + $Args
    & $psExe @argList
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed (exit={1})" -f $ScriptName, $LASTEXITCODE)
    }
}

Write-Host '=== Pixel7 HTTP setup -> start -> watch ===' -ForegroundColor Cyan

if (-not $PSBoundParameters.ContainsKey('ContinueOnGatewayFailure')) {
    $ContinueOnGatewayFailure = $true
}

if ($BootstrapGateway) {
    try {
        $bootstrapArgs = @()
        if ($RemoteOnly) { $bootstrapArgs += @('-DeviceSerial', '100.84.2.125:5555') }
        Invoke-Script -ScriptName 'pixel7_termux_bootstrap_http_gateway.ps1' -Args $bootstrapArgs
    }
    catch {
        if (-not $ContinueOnGatewayFailure) { throw }
        Write-Host ("[WARN] gateway bootstrap failed but continuing: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

try {
    $startArgs = @('-ApiPort', '5122', '-WaitListenSec', [string]$GatewayWaitListenSec)
    if ($RemoteOnly) { $startArgs += @('-DeviceSerial', '100.84.2.125:5555') }
    Invoke-Script -ScriptName 'pixel7_termux_start_http_gateway.ps1' -Args $startArgs
}
catch {
    if (-not $ContinueOnGatewayFailure) { throw }
    Write-Host ("[WARN] gateway start failed but continuing: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}

$watchArgs = @(
    '-IntervalSeconds', [string]$WatchIntervalSeconds,
    '-TimeoutSec', [string]$WatchTimeoutSec,
    '-FailThreshold', [string]$WatchFailThreshold
)
if ($RemoteOnly) { $watchArgs += '-RemoteOnly' }
if ($AttemptRecovery) { $watchArgs += '-AttemptRecovery' }
Invoke-Script -ScriptName 'pixel7_http_watch_start.ps1' -Args $watchArgs

Write-Host 'OK: HTTP gateway setup/start/watch done' -ForegroundColor Green
