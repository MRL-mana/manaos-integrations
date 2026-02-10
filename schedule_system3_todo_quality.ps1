# System3 Todo Quality Improvement Schedule Setup Script
# 毎日（デフォルト: 04:00）に品質改善バッチを実行

param(
    [string]$ScriptPath = "C:\Users\mana4\Desktop\manaos_integrations\todo_quality_improvement.py",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_Todo_Quality_Improvement",
    [string]$ScheduleTime = "04:00"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System3 Todo Quality Improvement Schedule" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Script Path: $ScriptPath" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Green
Write-Host "Schedule Time: $ScheduleTime" -ForegroundColor Green
Write-Host ""

$pythonFullPath = (Get-Command $PythonPath).Source
Write-Host "Python Full Path: $pythonFullPath" -ForegroundColor Gray
Write-Host ""

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Existing task removed" -ForegroundColor Green
}

$action = New-ScheduledTaskAction -Execute $pythonFullPath -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)
$trigger = New-ScheduledTaskTrigger -Daily -At $ScheduleTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 Todo Quality Improvement (update_quality_config_from_rejections)" -Force | Out-Null
    Write-Host "Scheduled task registered successfully!" -ForegroundColor Green
    Write-Host ""
    $nextRun = (Get-ScheduledTask -TaskName $TaskName).NextRunTime
    Write-Host "Next Run: $nextRun" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Delete: Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
