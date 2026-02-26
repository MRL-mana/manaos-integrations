param(
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min"
)

$ErrorActionPreference = "Stop"

Write-Host "=== R12 Health Watch Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 1
}

exit 0
