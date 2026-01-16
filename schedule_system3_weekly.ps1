# System3 Weekly Tasks Schedule Setup
# 週次タスク（日曜日23:30実行）

param(
    [string]$ScriptDir = "C:\Users\mana4\Desktop\manaos_integrations",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_Weekly_Tasks",
    [string]$ScheduleTime = "23:30",
    [string]$ScheduleDay = "Sunday"
)

Write-Host "System3 Weekly Tasks Schedule Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check script paths
$logRotationScript = Join-Path $ScriptDir "log_rotation_backup.py"
$playbookScript = Join-Path $ScriptDir "playbook_auto_promotion.py"

if (-not (Test-Path $logRotationScript)) {
    Write-Host "ERROR: Script not found: $logRotationScript" -ForegroundColor Red
    exit 1
}

Write-Host "Script Directory: $ScriptDir" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Green
Write-Host "Schedule: Every $ScheduleDay at $ScheduleTime" -ForegroundColor Green
Write-Host ""

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Existing task removed" -ForegroundColor Green
}

# Create PowerShell script that runs both tasks
$weeklyScript = Join-Path $ScriptDir "run_weekly_tasks.ps1"
$weeklyScriptContent = @"
# System3 Weekly Tasks Runner
# Runs log rotation and playbook promotion

Write-Host "System3 Weekly Tasks - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

# 1. Log rotation and backup
Write-Host "[1] Running log rotation and backup..." -ForegroundColor Yellow
& $PythonPath `"$logRotationScript`"
Write-Host ""

# 2. Playbook auto promotion
Write-Host "[2] Running playbook auto promotion..." -ForegroundColor Yellow
& $PythonPath `"$playbookScript`"
Write-Host ""

Write-Host "Weekly tasks completed" -ForegroundColor Green
"@

$weeklyScriptContent | Out-File -FilePath $weeklyScript -Encoding UTF8

# Create task action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$weeklyScript`"" -WorkingDirectory $ScriptDir

# Create trigger (weekly on Sunday)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $ScheduleTime

# Task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 Weekly Tasks (Log Rotation + Playbook Promotion)" -Force | Out-Null
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
