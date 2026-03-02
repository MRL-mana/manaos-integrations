param(
    [string]$TaskName = "ManaOS_OpenWebUI_Acceptance_Daily",
    [string]$StartTime = "08:30",
    [switch]$AlsoRegisterLightMonitor,
    [string]$LightTaskName = "ManaOS_OpenWebUI_Acceptance_Light_Monitor",
    [int]$LightIntervalMinutes = 5
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "run_openwebui_acceptance_daily_job.ps1"
$lightJobScript = Join-Path $scriptDir "run_openwebui_acceptance_status_monitor_job.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}
if ($AlsoRegisterLightMonitor -and (-not (Test-Path $lightJobScript))) {
    throw "Light monitor script not found: $lightJobScript"
}

if ($LightIntervalMinutes -lt 1 -or $LightIntervalMinutes -gt 1439) {
    throw "LightIntervalMinutes must be between 1 and 1439"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$jobScript`""
$lightTaskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$lightJobScript`""

Write-Host "=== Register OpenWebUI Acceptance Daily Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "StartTime: $StartTime" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
if ($AlsoRegisterLightMonitor) {
    Write-Host "LightTask: $LightTaskName (every $LightIntervalMinutes min)" -ForegroundColor Gray
    Write-Host "LightScr : $lightJobScript" -ForegroundColor Gray
}

schtasks /Create /SC DAILY /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($AlsoRegisterLightMonitor) {
    schtasks /Create /SC MINUTE /MO $LightIntervalMinutes /TN $LightTaskName /TR $lightTaskRun /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create light monitor task (exit=$LASTEXITCODE)"
    }

    Write-Host "[OK] Scheduled light monitor task created: $LightTaskName" -ForegroundColor Green
    schtasks /Query /TN $LightTaskName /V /FO LIST
}
