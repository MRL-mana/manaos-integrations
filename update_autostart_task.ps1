# ManaOS Auto-startup Task Updater
# Run this script as Administrator

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ManaOS Auto-startup Task Updater" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Admin check
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Administrator privileges required" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "`nPress Enter to exit"
    exit 1
}

try {
    # Remove existing task
    Write-Host "Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "ManaOS-Services" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
    
    # Create new task with batch file
    Write-Host "Creating new task with venv support..." -ForegroundColor Yellow
    
    $batchFile = "C:\Users\mana4\Desktop\manaos_integrations\start_manaos_autostart.bat"
    $workDir = "C:\Users\mana4\Desktop\manaos_integrations"
    
    $action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$batchFile`"" `
        -WorkingDirectory $workDir
    
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5) `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    
    $task = Register-ScheduledTask `
        -TaskName "ManaOS-Services" `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -RunLevel Highest `
        -Description "ManaOS VSCode/Cursor Integration Auto-startup (with venv)" `
        -Force
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " SUCCESS: Task updated!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    
    # Show configuration
    Write-Host "Task Configuration:" -ForegroundColor Cyan
    $task.Actions | Format-List Execute, Arguments, WorkingDirectory
    
    Write-Host "Task will run on Windows login" -ForegroundColor Green
    Write-Host "Using: start_manaos_autostart.bat (activates .venv)" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to update task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "`nPress Enter to exit"
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Read-Host "Press Enter to close"
