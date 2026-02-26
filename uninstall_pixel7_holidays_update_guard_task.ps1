param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual_Guard"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Uninstall Pixel7 Holiday Guard Task ===" -ForegroundColor Cyan
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

Write-Host "[OK] Scheduled guard task deleted: $TaskName" -ForegroundColor Green
