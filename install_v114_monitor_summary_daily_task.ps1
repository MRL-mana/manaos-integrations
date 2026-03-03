param(
    [string]$TaskName = 'ManaOS_v114_Monitor_Summary_Daily',
    [string]$StartTime = '09:10',
    [switch]$RunAsSystem,
    [switch]$NoFallbackToCurrentUser,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir 'summarize_v114_monitor_logs.ps1'

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($StartTime -notmatch '^([01]\d|2[0-3]):[0-5]\d$') {
    throw 'StartTime must be HH:mm (24h)'
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$jobScript`" -AsJson"
$useSystemAccount = $RunAsSystem.IsPresent

Write-Host '=== Register v114 Monitor Summary Daily Task ===' -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : DAILY $StartTime" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host '[INFO] PrintOnly mode: no task registration' -ForegroundColor Yellow
    exit 0
}

$createArgs = @('/Create', '/SC', 'DAILY', '/TN', $TaskName, '/TR', $taskRun, '/ST', $StartTime, '/F')
if ($useSystemAccount) {
    $createArgs += @('/RU', 'SYSTEM', '/RL', 'HIGHEST')
}

schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($useSystemAccount -and -not $NoFallbackToCurrentUser) {
        Write-Host '[WARN] SYSTEM registration failed. retry with current user...' -ForegroundColor Yellow
        $useSystemAccount = $false
        $createArgs = @('/Create', '/SC', 'DAILY', '/TN', $TaskName, '/TR', $taskRun, '/ST', $StartTime, '/F')
        schtasks @createArgs | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
        }
    }
    else {
        throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
    }
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
Write-Host "[OK] Effective Account : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}

exit 0