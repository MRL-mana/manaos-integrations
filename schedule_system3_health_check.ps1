# System3 Health Check Schedule Setup Script
# 各APIのヘルスチェックを定期的に実行（15分ごと）、失敗時はログに記録

param(
    [string]$ScriptPath = "C:\Users\mana4\Desktop\manaos_integrations\system3_health_check.py",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_Health_Check",
    [int]$IntervalMinutes = 15
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System3 Health Check Schedule Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

$fullPythonPath = (Get-Command $PythonPath -ErrorAction SilentlyContinue).Source
if (-not $fullPythonPath) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

Write-Host "Script: $ScriptPath" -ForegroundColor Green
Write-Host "Task: $TaskName" -ForegroundColor Green
Write-Host "Interval: Every $IntervalMinutes minutes" -ForegroundColor Green
Write-Host ""

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task" -ForegroundColor Yellow
}

$action = New-ScheduledTaskAction -Execute $fullPythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 API Health Check (log failures to logs/system3_health_check.log)" -Force | Out-Null
    Write-Host "Scheduled task registered!" -ForegroundColor Green
    Write-Host "Log: logs/system3_health_check.log" -ForegroundColor Gray
    Write-Host "Delete: Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
