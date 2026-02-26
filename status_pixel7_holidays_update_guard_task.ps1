param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual_Guard"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Pixel7 Holiday Guard Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 1
}

exit 0
