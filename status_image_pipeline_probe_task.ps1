param(
    [string]$TaskName = "ManaOS_Image_Pipeline_Probe_5min"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Image Pipeline Probe Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 1
}

exit 0
