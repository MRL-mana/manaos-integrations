param(
    [string]$TaskName = "ManaOS_OpenWebUI_Acceptance_Daily",
    [string]$StartTime = "08:30"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "run_openwebui_acceptance_daily_job.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$jobScript`""

Write-Host "=== Register OpenWebUI Acceptance Daily Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "StartTime: $StartTime" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray

schtasks /Create /SC DAILY /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST
