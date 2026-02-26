param(
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min",
    [string]$BaseUrl = "http://127.0.0.1:9510",
    [int]$IntervalMinutes = 5,
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "manaos-rpg\scripts\run_r12_health_watch.ps1"
$logPath = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw "IntervalMinutes must be 1..1440"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$jobScript`" -BaseUrl `"$BaseUrl`" -Once -FailOnError -JsonLogPath `"$logPath`""

Write-Host "=== Register R12 Health Watch Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $RunLevel" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "LogPath  : $logPath" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

$createTask = {
    param([string]$Level)
    schtasks /Create /SC MINUTE /MO $IntervalMinutes /TN $TaskName /TR $taskRun /RL $Level /F | Out-Null
    return $LASTEXITCODE
}

$exitCode = & $createTask $RunLevel
if ($exitCode -ne 0 -and $RunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) {
    Write-Host "[WARN] HIGHEST registration failed. retry with LIMITED..." -ForegroundColor Yellow
    $RunLevel = 'LIMITED'
    $exitCode = & $createTask $RunLevel
}
if ($exitCode -ne 0) {
    throw "Failed to create scheduled task (exit=$exitCode)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
Write-Host "[OK] Effective RunLevel: $RunLevel" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}
