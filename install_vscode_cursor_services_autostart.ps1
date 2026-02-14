# ManaOS VSCode/Cursor Services Auto-start (Scheduled Task)

param(
    [string]$TaskName = "ManaOS_VSCodeCursor_Services",
    [ValidateSet("Logon", "Startup")]
    [string]$Trigger = "Logon",
    [ValidateSet("Highest", "Limited")]
    [string]$RunLevel = "Highest"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "ManaOS VSCode/Cursor Services Auto-start Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check administrator privileges (required when RunLevel=Highest)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (($RunLevel -eq "Highest") -and (-not $isAdmin)) {
    Write-Host "Administrator privileges required for -RunLevel Highest." -ForegroundColor Yellow
    Write-Host "Run again as admin, or use -RunLevel Limited." -ForegroundColor Cyan
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $pythonExe) {
    $pythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $pythonExe) {
    Write-Host "Python not found (.venv/python/python3/py)." -ForegroundColor Red
    Write-Host "Expected venv path: $(Join-Path $repoRoot '.venv\Scripts\python.exe')" -ForegroundColor Gray
    exit 1
}

$managerScript = Join-Path $scriptDir "start_vscode_cursor_services.py"
if (-not (Test-Path $managerScript)) {
    Write-Host "Manager script not found: $managerScript" -ForegroundColor Red
    exit 1
}

Write-Host "Repo Root: $repoRoot" -ForegroundColor Gray
Write-Host "Python:    $pythonExe" -ForegroundColor Gray
Write-Host "Script:    $managerScript" -ForegroundColor Gray
Write-Host "TaskName:  $TaskName" -ForegroundColor Gray
Write-Host "Trigger:   $Trigger" -ForegroundColor Gray
Write-Host "RunLevel:  $RunLevel" -ForegroundColor Gray
Write-Host "" 

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Task action: run manager script with workspace venv python
$taskAction = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$managerScript`"" -WorkingDirectory $repoRoot

# Trigger
if ($Trigger -eq "Startup") {
    $triggerObj = New-ScheduledTaskTrigger -AtStartup
} else {
    $triggerObj = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
}

# Principal + settings
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel $RunLevel
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Hours 0)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $triggerObj -Principal $principal -Settings $settings -Description "ManaOS VSCode/Cursor services (Unified API / LLM Routing / Memory / Learning) auto-start" -Force | Out-Null

    Write-Host "[OK] Scheduled task registered." -ForegroundColor Green
    Write-Host "" 
    Write-Host "Verify:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "Start now:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Task registration failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
