# Register Remi API Auto-Start in Task Scheduler
# Run this ONCE as administrator

$taskName = "Remi-API-AutoStart"
$scriptPath = Join-Path $PSScriptRoot "start_remi_api.ps1"

# Remove existing task
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`"" `
    -WorkingDirectory $PSScriptRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-start Remi API (local_remi_api.py) on logon" `
    -Force

Write-Host ""
Write-Host "Task '$taskName' registered successfully!" -ForegroundColor Green
Write-Host "Remi API will auto-start on next logon." -ForegroundColor Cyan
Write-Host ""
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
