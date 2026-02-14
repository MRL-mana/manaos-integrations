# ManaOS VSCode/Cursor Services Auto-start Removal (Scheduled Task)

param(
    [string]$TaskName = "ManaOS_VSCodeCursor_Services"
)

Write-Host "ManaOS VSCode/Cursor Services Auto-start Removal" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existingTask) {
    Write-Host "Task not found: $TaskName" -ForegroundColor Yellow
    exit 0
}

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] Unregistered: $TaskName" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to unregister task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
