param(
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min",
    [string]$BaseUrl = "http://127.0.0.1:9510",
    [int]$IntervalMinutes = 5,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "manaos-rpg\scripts\run_r12_health_watch_once.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw "IntervalMinutes must be 1..1440"
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if (-not $NotifyOnSuccess.IsPresent -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
    $raw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
    if ($raw -in @('1','true','yes','on')) {
        $NotifyOnSuccess = $true
    }
}

$taskArgs = @(
    '-NoP',
    '-EP',
    'Bypass',
    '-File',
    "`"$jobScript`""
)

if ($BaseUrl -ne 'http://127.0.0.1:9510') {
    $taskArgs += @('-BaseUrl', "`"$BaseUrl`"")
}

if ($WebhookFormat -ne 'discord') {
    $taskArgs += @('-WebhookFormat', $WebhookFormat)
}

if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $taskArgs += @('-WebhookUrl', "`"$WebhookUrl`"")
    if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
        $taskArgs += @('-WebhookMention', "`"$WebhookMention`"")
    }
}
if ($NotifyOnSuccess.IsPresent) {
    $taskArgs += '-NotifyOnSuccess'
}

$taskRun = "pwsh " + ($taskArgs -join ' ')

Write-Host "=== Register R12 Health Watch Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $RunLevel" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
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
