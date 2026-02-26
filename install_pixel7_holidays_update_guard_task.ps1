param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual_Guard",
    [string]$StartTime = "04:10",
    [string]$Months = "JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC",
    [int]$Day = 1,
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "install_pixel7_holidays_update_task.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($Day -lt 1 -or $Day -gt 31) {
    throw "Day must be 1..31"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$jobScript`""

Write-Host "=== Register Pixel7 Holiday Guard Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MONTHLY $Months/$Day $StartTime" -ForegroundColor Gray
Write-Host "RunLevel : $RunLevel" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

schtasks /Create /SC MONTHLY /M $Months /D $Day /TN $TaskName /TR $taskRun /ST $StartTime /RL $RunLevel /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($RunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) {
        Write-Host "[WARN] HIGHEST registration failed. retry with LIMITED..." -ForegroundColor Yellow
        schtasks /Create /SC MONTHLY /M $Months /D $Day /TN $TaskName /TR $taskRun /ST $StartTime /RL LIMITED /F | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create scheduled guard task (exit=$LASTEXITCODE)"
        }
        Write-Host "[OK] Guard task created with LIMITED (fallback)" -ForegroundColor Green
    }
    else {
        throw "Failed to create scheduled guard task (exit=$LASTEXITCODE)"
    }
}

Write-Host "[OK] Scheduled guard task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled guard task triggered: $TaskName" -ForegroundColor Green
}
