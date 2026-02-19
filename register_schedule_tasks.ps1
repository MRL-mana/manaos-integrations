# ManaOS Moltbot Schedule Task Registration
# スケジュール実行タスク登録スクリプト

param(
    [string]$WorkspacePath = "c:\Users\mana4\Desktop\manaos_integrations"
)

# Administrator権限チェック
function Test-AdminPrivilege {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-AdminPrivilege)) {
    Write-Host "WARNING: Administrator privilege required" -ForegroundColor Yellow
    Write-Host "Please run this script with Administrator rights" -ForegroundColor Yellow
    exit 1
}

Write-Host "================================================"
Write-Host "  ManaOS Moltbot Schedule Task Registration"
Write-Host "================================================"
Write-Host ""

# Task definitions
$tasks = @(
    @{
        Name = "ManaOS_Moltbot_Morning_08"
        Time = "08:00:00"
        Description = "Morning auto-organize: Downloads file classification"
    },
    @{
        Name = "ManaOS_Moltbot_Noon_12"
        Time = "12:00:00"
        Description = "Noon auto-organize: Downloads file list and classify"
    },
    @{
        Name = "ManaOS_Moltbot_Evening_20"
        Time = "20:00:00"
        Description = "Evening auto-organize: Complete Downloads cleanup"
    }
)

# Script block for scheduled execution
$scriptBlock = @"
`$WorkspacePath = "$WorkspacePath"
cd `$WorkspacePath

# Set environment variables
`$env:EXECUTOR='moltbot'
`$env:MOLTBOT_CLI_PATH='C:\Users\mana4\AppData\Roaming\npm\openclaw'
`$env:MOLTBOT_GATEWAY_DATA_DIR='`$WorkspacePath\moltbot_gateway_data'
`$env:PYTHONPATH=`$WorkspacePath

# Log file
`$logFile = "`$WorkspacePath\logs\moltbot_schedule_`$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
New-Item -ItemType Directory -Path (Split-Path `$logFile) -Force -ErrorAction SilentlyContinue | Out-Null

# Execute
try {
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting Moltbot plan execution" | Tee-Object -FilePath `$logFile -Append
    python manaos_moltbot_runner.py organize_downloads | Tee-Object -FilePath `$logFile -Append
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Moltbot plan execution completed" | Tee-Object -FilePath `$logFile -Append
} catch {
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: `$_" | Tee-Object -FilePath `$logFile -Append
    exit 1
}
"@

$scriptPath = Join-Path $WorkspacePath "moltbot_scheduled_task.ps1"
$scriptBlock | Out-File -FilePath $scriptPath -Encoding UTF8 -Force
Write-Host "[OK] Script created: $scriptPath"
Write-Host ""

# Register each task
foreach ($task in $tasks) {
    Write-Host "Registering task: $($task.Name) at $($task.Time)" -ForegroundColor Yellow
    
    # Remove existing task
    $existingTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "  [INFO] Removing existing task..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false -ErrorAction SilentlyContinue
    }
    
    # Create trigger
    $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time
    
    # Create action
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" `
        -WorkingDirectory $WorkspacePath
    
    # Create settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -RunWithoutNetwork $false `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable $true
    
    # Create principal
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest
    
    # Register task
    try {
        Register-ScheduledTask `
            -TaskName $task.Name `
            -TaskPath "\ManaOS\" `
            -Trigger $trigger `
            -Action $action `
            -Settings $settings `
            -Principal $principal `
            -Description $task.Description `
            -Force -ErrorAction Stop | Out-Null
        
        Write-Host "  [OK] Task registered successfully at $($task.Time)" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Failed to register task: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "================================================"
Write-Host "  Schedule Registration Complete!"
Write-Host "================================================"
Write-Host ""
Write-Host "Registered tasks:"
Write-Host "  Morning (08:00) - ManaOS_Moltbot_Morning_08"
Write-Host "  Noon (12:00)   - ManaOS_Moltbot_Noon_12"
Write-Host "  Evening (20:00)- ManaOS_Moltbot_Evening_20"
Write-Host ""
Write-Host "Verification:"
Write-Host "  1. Open Windows Task Scheduler"
Write-Host "  2. Navigate to [Task Scheduler Library] > [ManaOS]"
Write-Host "  3. Verify three tasks are listed above"
Write-Host ""
Write-Host "Log location:"
Write-Host "  $WorkspacePath\logs\moltbot_schedule_*.log"
Write-Host ""
