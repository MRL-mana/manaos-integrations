param(
    [string]$TaskName = "ManaOS_WSL_Docker_Health",
    [int]$IntervalMinutes = 15,
    [string]$Distro = "Ubuntu-22.04",
    [switch]$EnableRecovery = $true,
    [int]$TimeoutSec = 90
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1439) {
    throw "IntervalMinutes must be between 1 and 1439"
}

if ($TimeoutSec -lt 10 -or $TimeoutSec -gt 900) {
    throw "TimeoutSec must be between 10 and 900"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "check_wsl_docker_health.ps1"
if (-not (Test-Path $jobScript)) {
    throw "Health script not found: $jobScript"
}

$recoverArg = if ($EnableRecovery) { "-Recover" } else { "" }
$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$jobScript`" -Distro `"$Distro`" -TimeoutSec $TimeoutSec $recoverArg"

Write-Host "=== Register WSL/Docker Health Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Interval : every $IntervalMinutes minute(s)" -ForegroundColor Gray
Write-Host "Distro   : $Distro" -ForegroundColor Gray
Write-Host "Recover  : $EnableRecovery" -ForegroundColor Gray
Write-Host "Timeout  : $TimeoutSec sec" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray

schtasks /Create /SC MINUTE /MO $IntervalMinutes /TN $TaskName /TR $taskRun /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST
