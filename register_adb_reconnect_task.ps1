# Register ADB Auto-Reconnect as Windows Startup Task
# Run this script once with admin privileges

$taskName = "Remi-ADB-AutoReconnect"
$scriptPath = "C:\Users\mana4\Desktop\manaos_integrations\adb_auto_reconnect.ps1"

# Remove existing task if any
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create task action
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

# Trigger: at user logon
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # No time limit

# Register
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-reconnect ADB to Pixel 7a via Tailscale (port 5555)" `
    -RunLevel Highest

Write-Host "Task '$taskName' registered successfully!" -ForegroundColor Green
Write-Host "Will run at every logon as $env:USERNAME"
