param(
    [int]$R12IntervalMinutes = 15,
    [int]$RLIntervalMinutes = 15,
    [int]$OpsWatchIntervalMinutes = 15,
    [switch]$SkipOpsWatch,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Setup R12 + RL Operations ===" -ForegroundColor Cyan
Write-Host "R12 interval: $R12IntervalMinutes min" -ForegroundColor Gray
Write-Host "RL interval : $RLIntervalMinutes min" -ForegroundColor Gray

$r12Installer = Join-Path $scriptDir "install_r12_health_watch_task.ps1"
$rlInstaller = Join-Path $scriptDir "install_rl_anything_bootstrap_task.ps1"
$opsWatchInstaller = Join-Path $scriptDir "install_r12_rl_ops_watch_task.ps1"
$r12Status = Join-Path $scriptDir "status_r12_health_watch_task.ps1"
$rlStatus = Join-Path $scriptDir "status_rl_anything_bootstrap_task.ps1"
$opsWatchStatus = Join-Path $scriptDir "status_r12_rl_ops_watch_task.ps1"

if (-not (Test-Path $r12Installer)) { throw "Not found: $r12Installer" }
if (-not (Test-Path $rlInstaller)) { throw "Not found: $rlInstaller" }
if (-not $SkipOpsWatch.IsPresent -and -not (Test-Path $opsWatchInstaller)) { throw "Not found: $opsWatchInstaller" }

$r12Args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$r12Installer,'-IntervalMinutes',"$R12IntervalMinutes")
$rlArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$rlInstaller,'-IntervalMinutes',"$RLIntervalMinutes")
$opsWatchArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$opsWatchInstaller,'-IntervalMinutes',"$OpsWatchIntervalMinutes")
if ($RunNow.IsPresent) {
    $r12Args += '-RunNow'
    $rlArgs += '-RunNow'
    if (-not $SkipOpsWatch.IsPresent) {
        $opsWatchArgs += '-RunNow'
    }
}

pwsh @r12Args
pwsh @rlArgs
if (-not $SkipOpsWatch.IsPresent) {
    pwsh @opsWatchArgs
}

Write-Host "" 
Write-Host "=== Status After Setup ===" -ForegroundColor Cyan
pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Status
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlStatus
if (-not $SkipOpsWatch.IsPresent) {
    pwsh -NoProfile -ExecutionPolicy Bypass -File $opsWatchStatus
}
