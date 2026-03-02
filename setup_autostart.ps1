# Auto-start setup script
# Register to Windows Task Scheduler to auto-start monitoring system on boot

# Check administrator privileges and restart as admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] Administrator privileges required" -ForegroundColor Yellow
    Write-Host "Restarting script with administrator privileges..." -ForegroundColor Cyan
    Write-Host ""
    
    # Get the script path
    $scriptPath = $MyInvocation.MyCommand.Path
    $arguments = "-ExecutionPolicy Bypass -File `"$scriptPath`""
    
    # Start new PowerShell process as administrator
    Start-Process powershell -Verb RunAs -ArgumentList $arguments
    
    # Exit current process
    exit 0
}

Write-Host "=== Auto-start Setup ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Task name
$taskName = "ManaOS_DeviceMonitoring"

# Check existing task
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "[INFO] Existing task found: $taskName" -ForegroundColor Yellow
    Write-Host "Overwrite? (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "Setup cancelled" -ForegroundColor Yellow
        exit 0
    }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "[OK] Existing task removed" -ForegroundColor Green
}

# Start script path
$startScript = Join-Path $scriptDir "start_device_monitoring.ps1"

if (-not (Test-Path $startScript)) {
    Write-Host "[ERROR] Start script not found: $startScript" -ForegroundColor Red
    exit 1
}

# Create task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`"" -WorkingDirectory $scriptDir

# Create trigger (at startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Register task
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "ManaOS Device Health Monitor - Auto start on system boot"
    
    Write-Host ""
    Write-Host "[OK] Auto-start setup completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Settings:" -ForegroundColor Cyan
    Write-Host "  Task Name: $taskName" -ForegroundColor White
    Write-Host "  Trigger: At Startup" -ForegroundColor White
    Write-Host "  User: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor White
    Write-Host ""
    Write-Host "Verify:" -ForegroundColor Cyan
    Write-Host "  Open Task Scheduler and check $taskName" -ForegroundColor White
    Write-Host "  Or: Get-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host ""
    Write-Host "Test run:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "[ERROR] Task registration failed: $_" -ForegroundColor Red
    exit 1
}
