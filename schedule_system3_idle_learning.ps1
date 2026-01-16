# System3 Idle Learning Schedule Setup Script
# アイドル学習を定期的にチェック（5分ごと）

param(
    [string]$ScriptPath = "C:\Users\mana4\Desktop\manaos_integrations\system3_idle_learning.py",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_Idle_Learning",
    [int]$IntervalMinutes = 5
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System3 Idle Learning Schedule Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Ensure UTF-8 for PowerShell output
$env:PYTHONUTF8="1"
chcp 65001 | Out-Null

# Check script path
if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ ERROR: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

# Resolve full Python path
$fullPythonPath = (Get-Command $PythonPath -ErrorAction SilentlyContinue).Source
if (-not $fullPythonPath) {
    Write-Host "❌ ERROR: Python executable not found. Please ensure 'python' is in your PATH." -ForegroundColor Red
    exit 1
}

Write-Host "Script Path: $ScriptPath" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Green
Write-Host "Check Interval: Every $IntervalMinutes minutes" -ForegroundColor Green
Write-Host ""
Write-Host "Python Full Path: $fullPythonPath" -ForegroundColor Gray
Write-Host ""

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ Existing task removed" -ForegroundColor Green
}

# Create task action
$action = New-ScheduledTaskAction -Execute $fullPythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)

# Create trigger (every N minutes, starting from now)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 365)

# Task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 Idle Learning (Background Learning when idle)" -Force | Out-Null
    Write-Host "✅ Scheduled task registered successfully!" -ForegroundColor Green
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
    Write-Host "❌ ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Note: Idle learning will only execute when:" -ForegroundColor Yellow
Write-Host "  - CPU < 20% for 10 minutes" -ForegroundColor Gray
Write-Host "  - Memory < 70%" -ForegroundColor Gray
Write-Host "  - No user input for 30 minutes" -ForegroundColor Gray
Write-Host "  - Max 2 executions per day" -ForegroundColor Gray
Write-Host "  - Max 10 minutes per execution" -ForegroundColor Gray
Write-Host ""
