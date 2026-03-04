param(
    [switch]$RemoteOnly,
    [switch]$RestartAdbOnStart,
    [switch]$AttemptHttpRecovery,
    [switch]$BootstrapGateway,
    [switch]$SkipGatewayStart,
    [switch]$ContinueOnGatewayFailure,
    [int]$KeepaliveIntervalSeconds = 60,
    [int]$HttpWatchIntervalSeconds = 15,
    [int]$HttpWatchFailThreshold = 3,
    [int]$HttpWatchTimeoutSec = 3
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
if (-not $psExe) { $psExe = 'powershell' }

function Invoke-Script {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptName,
        [string[]]$Args = @(),
        [switch]$IgnoreExitCode
    )

    $scriptPath = Join-Path $root $ScriptName
    if (-not (Test-Path $scriptPath)) {
        throw "not found: $scriptPath"
    }

    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath) + $Args
    & $psExe @argList
    $code = $LASTEXITCODE
    if (-not $IgnoreExitCode -and $code -ne 0) {
        throw ("{0} failed (exit={1})" -f $ScriptName, $code)
    }
}

function Start-KeepaliveIfNeeded {
    $pidFile = Join-Path $root '.pixel7_adb_keepalive.pid'
    if (Test-Path $pidFile) {
        $pidText = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
        if ($pidText -match '^\d+$') {
            $p = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host ("keepalive already running (PID={0})" -f $pidText) -ForegroundColor Yellow
                return
            }
        }
    }

    $scriptPath = Join-Path $root 'pixel7_adb_keepalive.ps1'
    if (-not (Test-Path $scriptPath)) { throw "not found: $scriptPath" }

    $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $scriptPath, '-IntervalSeconds', [string]$KeepaliveIntervalSeconds)
    if ($RemoteOnly) { $args += '-RemoteOnly' }
    if ($RestartAdbOnStart) { $args += '-RestartAdbOnStart' }

    $sp = @{
        FilePath     = $psExe
        ArgumentList = $args
        PassThru     = $true
        WindowStyle  = 'Hidden'
    }

    $p = Start-Process @sp
    Write-Host ("keepalive started (PID={0})" -f $p.Id) -ForegroundColor Green
}

Write-Host '=== Pixel7 full resident + HTTP start ===' -ForegroundColor Cyan

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

if (-not $SkipGatewayStart) {
    try {
        $startGatewayArgs = @('-ApiPort', '5122', '-WaitListenSec', '120')
        if ($RemoteOnly) { $startGatewayArgs += @('-DeviceSerial', '100.84.2.125:5555') }
        Invoke-Script -ScriptName 'pixel7_termux_start_http_gateway.ps1' -Args $startGatewayArgs
    }
    catch {
        if (-not $ContinueOnGatewayFailure) { throw }
        Write-Host ("[WARN] gateway start failed but continuing: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

Start-KeepaliveIfNeeded

$scrcpyArgs = @('-Hidden', '-TurnScreenOff')
if ($RemoteOnly) { $scrcpyArgs += '-RemoteOnly' }
if ($RestartAdbOnStart) { $scrcpyArgs += '-KillExisting' }
Invoke-Script -ScriptName 'pixel7_scrcpy_watch_start.ps1' -Args $scrcpyArgs

$rebootArgs = @('-Hidden', '-IntervalSeconds', '30')
if ($RemoteOnly) { $rebootArgs += '-RemoteOnly' }
if ($RestartAdbOnStart) { $rebootArgs += '-RestartAdbOnStart' }
Invoke-Script -ScriptName 'pixel7_reboot_watch_start.ps1' -Args $rebootArgs

$httpArgs = @(
    '-IntervalSeconds', [string]$HttpWatchIntervalSeconds,
    '-TimeoutSec', [string]$HttpWatchTimeoutSec,
    '-FailThreshold', [string]$HttpWatchFailThreshold,
    '-RemoteOnly'
)
if (-not $RemoteOnly) {
    $httpArgs = @(
        '-IntervalSeconds', [string]$HttpWatchIntervalSeconds,
        '-TimeoutSec', [string]$HttpWatchTimeoutSec,
        '-FailThreshold', [string]$HttpWatchFailThreshold
    )
}
if ($AttemptHttpRecovery) { $httpArgs += '-AttemptRecovery' }
Invoke-Script -ScriptName 'pixel7_http_watch_start.ps1' -Args $httpArgs

Write-Host 'OK: keepalive + scrcpy watch + reboot watch + http watch started' -ForegroundColor Green
