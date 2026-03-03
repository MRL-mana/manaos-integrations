param(
    [string]$TaskName = 'ManaOS_v114_Waiting_Alert_10min',
    [int]$IntervalMinutes = 10,
    [int]$WaitingAlertMinutes = 30,
    [int]$NotifyCooldownMinutes = 60,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = 'discord',
    [string]$WebhookUrl = '',
    [string]$WebhookMention = '',
    [switch]$RunAsSystem,
    [switch]$NoFallbackToCurrentUser,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir 'check_v114_monitor_waiting_alert.ps1'
$configPath = Join-Path $scriptDir 'logs\v114_waiting_alert_task.config.json'

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}
if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw 'IntervalMinutes must be 1..1440'
}
if ($WaitingAlertMinutes -lt 1) {
    throw 'WaitingAlertMinutes must be >= 1'
}
if ($NotifyCooldownMinutes -lt 0) {
    throw 'NotifyCooldownMinutes must be >= 0'
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}

$configObj = [ordered]@{
    summary_file = Join-Path $scriptDir 'logs\v114_monitor_summary_latest.json'
    checkpoint = 4500
    waiting_alert_minutes = [int]$WaitingAlertMinutes
    notify_cooldown_minutes = [int]$NotifyCooldownMinutes
    state_file = Join-Path $scriptDir 'logs\v114_waiting_alert_state.json'
    webhook_format = [string]$WebhookFormat
    webhook_url = [string]$WebhookUrl
    webhook_mention = [string]$WebhookMention
    refresh_summary = $true
}
$configObj | ConvertTo-Json -Depth 6 | Set-Content -Path $configPath -Encoding UTF8

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$jobScript`""
$useSystemAccount = $RunAsSystem.IsPresent

Write-Host '=== Register v114 Waiting Alert Task ===' -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Config   : $configPath" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host '[INFO] PrintOnly mode: no task registration' -ForegroundColor Yellow
    exit 0
}

$createArgs = @('/Create', '/SC', 'MINUTE', '/MO', "$IntervalMinutes", '/TN', $TaskName, '/TR', $taskRun, '/F')
if ($useSystemAccount) {
    $createArgs += @('/RU', 'SYSTEM', '/RL', 'HIGHEST')
}

schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($useSystemAccount -and -not $NoFallbackToCurrentUser) {
        Write-Host '[WARN] SYSTEM registration failed. retry with current user...' -ForegroundColor Yellow
        $useSystemAccount = $false
        $createArgs = @('/Create', '/SC', 'MINUTE', '/MO', "$IntervalMinutes", '/TN', $TaskName, '/TR', $taskRun, '/F')
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
