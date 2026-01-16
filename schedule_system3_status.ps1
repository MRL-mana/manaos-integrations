# System3 Status Auto Schedule Setup Script
# Run daily at 23:00

param(
    [string]$ScriptPath = "C:\Users\mana4\Desktop\manaos_integrations\create_system3_status.py",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_Status_Update",
    [string]$ScheduleTime = "23:00"
)

Write-Host "System3 Status Auto Schedule Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check script path
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Script Path: $ScriptPath" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Green
Write-Host "Schedule Time: $ScheduleTime" -ForegroundColor Green
Write-Host ""

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Existing task removed" -ForegroundColor Green
}

# Create task action
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)

# Create trigger (daily at specified time)
$trigger = New-ScheduledTaskTrigger -Daily -At $ScheduleTime

# Task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 Status Auto Update (Phase B)" -Force | Out-Null
    Write-Host "Scheduled task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Run:" -ForegroundColor Cyan
    $nextRun = (Get-ScheduledTask -TaskName $TaskName).NextRunTime
    Write-Host "  $nextRun" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check command:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Delete command:" -ForegroundColor Cyan
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
