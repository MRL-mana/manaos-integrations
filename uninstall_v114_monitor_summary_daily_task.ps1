param(
    [string]$TaskName = 'ManaOS_v114_Monitor_Summary_Daily'
)

$ErrorActionPreference = 'Stop'

Write-Host '=== Uninstall v114 Monitor Summary Daily Task ===' -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
Write-Host "[OK] Scheduled task deleted: $TaskName" -ForegroundColor Green
exit 0
