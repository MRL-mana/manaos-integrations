param(
    [string]$TaskName = "ManaOS_RLAnything_Bootstrap_Logon"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Unregister RLAnything Bootstrap Task ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

schtasks /Delete /TN $TaskName /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to delete task (or not found): $TaskName"
}

Write-Host "[OK] Task deleted: $TaskName" -ForegroundColor Green
