param(
    [switch]$KeepStatus,
    [switch]$SkipGatewayStop
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$psExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
if (-not $psExe) { $psExe = 'powershell' }

function Invoke-ScriptBestEffort {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptName,
        [string[]]$Args = @()
    )

    $scriptPath = Join-Path $root $ScriptName
    if (-not (Test-Path $scriptPath)) {
        Write-Host ("skip (not found): {0}" -f $ScriptName) -ForegroundColor Yellow
        return $false
    }

    try {
        $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath) + $Args
        & $psExe @argList
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host ("NG: {0} (exit={1})" -f $ScriptName, $code) -ForegroundColor Yellow
            return $false
        }

        Write-Host ("OK: {0}" -f $ScriptName) -ForegroundColor Green
        return $true
    } catch {
        Write-Host ("NG: {0} ({1})" -f $ScriptName, $_.Exception.Message) -ForegroundColor Yellow
        return $false
    }
}

Write-Host '=== Pixel7 full resident + HTTP stop ===' -ForegroundColor Cyan

$allOk = $true

if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_http_watch_stop.ps1')) { $allOk = $false }

$edgeStopArgs = @('-Force')
if ($KeepStatus) { $edgeStopArgs += '-KeepStatus' }
if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_edge_watch_stop.ps1' -Args $edgeStopArgs)) { $allOk = $false }

if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_scrcpy_watch_stop.ps1' -Args @('-KillScrcpy'))) { $allOk = $false }

$rebootStopArgs = @()
if ($KeepStatus) { $rebootStopArgs += '-KeepStatus' }
if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_reboot_watch_stop.ps1' -Args $rebootStopArgs)) { $allOk = $false }

if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_adb_keepalive_stop.ps1')) { $allOk = $false }

if (-not $SkipGatewayStop) {
    if (-not (Invoke-ScriptBestEffort -ScriptName 'pixel7_termux_stop_http_gateway.ps1')) { $allOk = $false }
}

if ($allOk) {
    Write-Host 'OK: all stop operations completed' -ForegroundColor Green
    exit 0
}

Write-Host 'DONE with warnings: some components failed to stop cleanly' -ForegroundColor Yellow
exit 1
