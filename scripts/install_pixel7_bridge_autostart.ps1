# Pixel 7 ADB bridge - register "run at logon" task (Task Scheduler)
# Uses Tailscale first, then USB. Run as Admin to register.
if ($PSScriptRoot) {
    $root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $root = (Get-Location).Path
}
$bridgeScript = Join-Path $root "start_pixel7_bridge_auto.ps1"
$taskName = "ManaOS_Pixel7_Bridge"
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) { $pythonPath = "python" }

if (-not (Test-Path $bridgeScript)) {
    Write-Host "Not found: $bridgeScript" -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$bridgeScript`"" `
    -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
    Write-Host "[OK] Task updated: $taskName (Pixel7 bridge at logon, Tailscale first)" -ForegroundColor Green
} else {
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
        Write-Host "[OK] Task registered: $taskName (Pixel7 bridge at logon, Tailscale first)" -ForegroundColor Green
    } catch {
        Write-Host "[INFO] Admin rights may be required to register the task." -ForegroundColor Yellow
        Write-Host "       To start manually: $bridgeScript" -ForegroundColor Gray
        Write-Host "       Or run start_all_optionals.ps1 and choose 6" -ForegroundColor Gray
    }
}
Write-Host ""
Write-Host "To remove task: Unregister-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
