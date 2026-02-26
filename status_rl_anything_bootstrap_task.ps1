param(
    [string]$TaskName = "ManaOS_RLAnything_Bootstrap_Logon"
)

$ErrorActionPreference = "Stop"

Write-Host "=== RLAnything Bootstrap Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
Write-Host ""

schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "Task not found: $TaskName"
}
