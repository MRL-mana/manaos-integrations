param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual",
    [string]$StartTime = "03:30",
    [string]$Month = "DEC",
    [int]$Day = 25,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "update_pixel7_holidays_jp.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($Day -lt 1 -or $Day -gt 31) {
    throw "Day must be 1..31"
}

$validMonths = @('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
$monthUpper = $Month.Trim().ToUpperInvariant()
if ($monthUpper -notin $validMonths) {
    throw "Month must be JAN..DEC"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$jobScript`" -IncludeNextYear"

Write-Host "=== Register Pixel7 Holiday Update Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MONTHLY $monthUpper/$Day $StartTime" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

schtasks /Create /SC MONTHLY /M $monthUpper /D $Day /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}
