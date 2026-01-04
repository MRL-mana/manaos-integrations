# X280 API Gateway Auto-start Setup
# This script registers the X280 API Gateway to start automatically on Windows startup

# Check administrator privileges and restart as admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] Administrator privileges required" -ForegroundColor Yellow
    Write-Host "Restarting script with administrator privileges..." -ForegroundColor Cyan
    Write-Host ""
    
    # Get the script path
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.ScriptName
    }
    
    # Get all arguments
    $arguments = "-ExecutionPolicy Bypass -File `"$scriptPath`""
    
    # Add original arguments if any
    if ($args.Count -gt 0) {
        $arguments += " " + ($args -join " ")
    }
    
    # Start new PowerShell process as administrator
    try {
        Start-Process powershell -Verb RunAs -ArgumentList $arguments -Wait
        exit 0
    } catch {
        Write-Host "[ERROR] Failed to restart with administrator privileges: $_" -ForegroundColor Red
        Write-Host "Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Manual steps:" -ForegroundColor Yellow
        Write-Host "1. Right-click PowerShell" -ForegroundColor White
        Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
        Write-Host "3. Run: cd C:\manaos_x280" -ForegroundColor White
        Write-Host "4. Run: .\x280_setup_autostart.ps1" -ForegroundColor White
        exit 1
    }
}

Write-Host "=== X280 API Gateway Auto-start Setup ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[OK] Running with administrator privileges" -ForegroundColor Green
Write-Host ""

# Get script directory (handle both direct execution and admin restart)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir -or $scriptDir -eq "") {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
}
if (-not $scriptDir -or $scriptDir -eq "") {
    # Fallback: use current directory
    $scriptDir = Get-Location
}

Write-Host "[INFO] Script directory: $scriptDir" -ForegroundColor Gray

# Task configuration
$taskName = "ManaOS_X280_API_Gateway"
$scriptPath = Join-Path $scriptDir "x280_api_gateway_start.ps1"

Write-Host "[INFO] Script path: $scriptPath" -ForegroundColor Gray

# Check if script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
    Write-Host "[INFO] Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "[INFO] Files in script directory:" -ForegroundColor Yellow
    Get-ChildItem $scriptDir -Filter "*.ps1" | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }
    exit 1
}

Write-Host "[1/3] Checking existing task..." -ForegroundColor Yellow
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "[INFO] Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "[OK] Old task removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/3] Creating scheduled task..." -ForegroundColor Yellow

# Create action
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`""

# Create trigger (at startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -RunLevel Highest

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register task
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "ManaOS X280 API Gateway Auto-start" | Out-Null
    
    if ($LASTEXITCODE -eq 0 -or $?) {
        Write-Host "[OK] Task registered successfully" -ForegroundColor Green
    } else {
        throw "Register-ScheduledTask returned non-zero exit code"
    }
} catch {
    Write-Host "[ERROR] Failed to register task: $_" -ForegroundColor Red
    Write-Host "[DEBUG] Task Name: $taskName" -ForegroundColor Yellow
    Write-Host "[DEBUG] Script Path: $scriptPath" -ForegroundColor Yellow
    Write-Host "[DEBUG] User: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Trying alternative method..." -ForegroundColor Yellow
    
    # Try alternative method without principal
    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description "ManaOS X280 API Gateway Auto-start" | Out-Null
        Write-Host "[OK] Task registered successfully (alternative method)" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Alternative method also failed: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[3/3] Verifying task..." -ForegroundColor Yellow
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    Write-Host "[OK] Task verified" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== Auto-start Setup Complete ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Task Name: $taskName" -ForegroundColor White
    Write-Host "Trigger: At Startup" -ForegroundColor White
    Write-Host "User: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor White
    Write-Host ""
    Write-Host "Verify: Open Task Scheduler and check '$taskName'" -ForegroundColor Yellow
    Write-Host "Or: Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Test run: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
} else {
    Write-Host "[ERROR] Task verification failed" -ForegroundColor Red
    exit 1
}

