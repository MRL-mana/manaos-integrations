# Ollama GPU Mode Auto-start Setup (WSL2)
# Register to Windows Task Scheduler to auto-start Ollama in GPU mode on boot

Write-Host "=== Ollama GPU Mode Auto-start Setup ===" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[WARN] Administrator privileges required" -ForegroundColor Yellow
    Write-Host "Restarting with administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$taskName = "ManaOS_Ollama_GPU_WSL2"
$scriptPath = Join-Path $PSScriptRoot "start_ollama_gpu.ps1"

# Check if script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Write-Host "`nCreating scheduled task..." -ForegroundColor Yellow

try {
    # Create action (run PowerShell script)
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`"" `
        -WorkingDirectory $PSScriptRoot

    # Create trigger (at startup, delay 30 seconds for WSL2 to be ready)
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT30S"  # 30 seconds delay

    # Create principal (run as current user)
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Highest

    # Create settings (allow start on battery, don't stop on battery, restart on failure)
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0)

    # Register task
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "ManaOS Ollama GPU Mode (WSL2) - Auto-start on system boot" `
        -ErrorAction Stop | Out-Null

    Write-Host "[OK] Auto-start setup completed!" -ForegroundColor Green
    Write-Host "`nTask Details:" -ForegroundColor Cyan
    Write-Host "  Task Name: $taskName" -ForegroundColor White
    Write-Host "  Trigger: At Startup (30s delay)" -ForegroundColor White
    Write-Host "  Script: $scriptPath" -ForegroundColor White
    Write-Host "  Auto-restart: Yes (up to 3 times)" -ForegroundColor White
    Write-Host "`nTo verify:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName `"$taskName`"" -ForegroundColor White
    Write-Host "  Or open Task Scheduler and check `"$taskName`"" -ForegroundColor White

} catch {
    Write-Host "[ERROR] Auto-start setup failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Ollama will automatically start in GPU mode on system boot." -ForegroundColor Green
