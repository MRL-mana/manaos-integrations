param(
    [string]$TaskName = "ManaOS_Reason_Enum_Lint_Cooldown_Verify_Weekly"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Uninstall Reason Enum Cooldown Verify Task ===" -ForegroundColor Cyan
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
