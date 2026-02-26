param(
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Uninstall R12 Health Watch Task ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

schtasks /Query /TN $TaskName *> $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 0
}

schtasks /Delete /TN $TaskName /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to delete scheduled task (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Scheduled task deleted: $TaskName" -ForegroundColor Green
