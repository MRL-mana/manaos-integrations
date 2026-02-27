param(
    [string]$TaskName = "ManaOS_RLAnything_Bootstrap_Logon",
    [int]$IntervalMinutes = 15,
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw "IntervalMinutes must be 1..1440"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "scripts\start_rl_anything.ps1"
$runnerScript = Join-Path $scriptDir "run_rl_anything_bootstrap_once.ps1"
$configPath = Join-Path $scriptDir "logs\rl_anything_bootstrap_task.config.json"

if (-not (Test-Path $jobScript)) {
    throw "Script not found: $jobScript"
}

if (-not (Test-Path $runnerScript)) {
    throw "Runner script not found: $runnerScript"
}

$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$configObj = [ordered]@{
    task_name = $TaskName
    script_path = $jobScript
    enable = $true
    dashboard = $true
}
$configObj | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8

$taskArgs = @(
    '-NoP',
    '-EP',
    'Bypass',
    '-File',
    "`"$runnerScript`"",
    '-ConfigFile',
    "`"$configPath`""
)

$taskRun = "pwsh " + ($taskArgs -join ' ')

Write-Host "=== Register RLAnything Bootstrap Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $RunLevel" -ForegroundColor Gray
Write-Host "Script   : $runnerScript" -ForegroundColor Gray
Write-Host "Config   : $configPath" -ForegroundColor Gray
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

$createTaskForUser = {
    schtasks /Create /SC MINUTE /MO $IntervalMinutes /TN $TaskName /TR $taskRun /RU $env:USERNAME /IT /F | Out-Null
    return $LASTEXITCODE
}

$exitCode = & $createTask $RunLevel
if ($exitCode -ne 0 -and $RunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) {
    Write-Host "[WARN] HIGHEST registration failed. retry with LIMITED..." -ForegroundColor Yellow
    $RunLevel = 'LIMITED'
    $exitCode = & $createTask $RunLevel
}
if ($exitCode -ne 0) {
    Write-Host "[WARN] Standard registration failed. retry with current user interactive mode..." -ForegroundColor Yellow
    $exitCode = & $createTaskForUser
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
