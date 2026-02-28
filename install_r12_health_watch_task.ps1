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
    [switch]$RunAsSystem,
    [switch]$KeepBatteryRestrictions,
    [switch]$NoFallbackToCurrentUser,
    [switch]$NoFallbackToLimited,
    [string]$ConfigFile = "",
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "manaos-rpg\scripts\run_r12_health_watch_once.ps1"
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\r12_health_watch_task.config.json"
}

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
    "`"$jobScript`"",
    '-ConfigFile',
    "`"$ConfigFile`""
)

$taskRun = "pwsh -WindowStyle Hidden " + ($taskArgs -join ' ')
$effectiveRunLevel = $RunLevel
$useSystemAccount = $RunAsSystem.IsPresent
if ($RunAsSystem.IsPresent -and $effectiveRunLevel -eq 'LIMITED') {
    $effectiveRunLevel = 'HIGHEST'
}

function Set-TaskBatteryPolicy {
    param(
        [string]$InTaskName,
        [switch]$Skip
    )

    if ($Skip.IsPresent) {
        Write-Host "[INFO] Keep battery restrictions enabled" -ForegroundColor DarkGray
        return
    }

    try {
        $service = New-Object -ComObject 'Schedule.Service'
        $service.Connect()
        $root = $service.GetFolder('\\')
        $taskPath = if ($InTaskName.StartsWith('\\')) { $InTaskName } else { "\\$InTaskName" }
        $task = $root.GetTask($taskPath)
        if ($null -eq $task) {
            Write-Host "[WARN] Task not found for battery policy update: $InTaskName" -ForegroundColor Yellow
            return
        }

        $definition = $task.Definition
        $definition.Settings.DisallowStartIfOnBatteries = $false
        $definition.Settings.StopIfGoingOnBatteries = $false
        $definition.Settings.WakeToRun = $true
        $principal = $definition.Principal
        $userId = $principal.UserId
        if ([string]::IsNullOrWhiteSpace($userId)) {
            $userId = $null
        }
        $logonType = [int]$principal.LogonType
        $null = $root.RegisterTaskDefinition($taskPath, $definition, 6, $userId, $null, $logonType, $null)
        Write-Host "[OK] Battery policy relaxed (start/continue on battery, wake enabled)" -ForegroundColor Green
    } catch {
        $msg = $_.Exception.Message
        if ($msg -match '0x8007007B') {
            Write-Host "[INFO] Battery policy update skipped (task remains valid): $msg" -ForegroundColor DarkGray
            return
        }
        Write-Host "[WARN] Failed to update battery policy: $msg" -ForegroundColor Yellow
    }
}

Write-Host "=== Register R12 Health Watch Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $effectiveRunLevel" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Config   : $ConfigFile" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

$configDir = Split-Path -Parent $ConfigFile
if (-not [string]::IsNullOrWhiteSpace($configDir) -and -not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$configPayload = [ordered]@{
    task_name = $TaskName
    base_url = $BaseUrl
    interval_minutes = $IntervalMinutes
    webhook_format = $WebhookFormat
    webhook_url = $WebhookUrl
    webhook_mention = $WebhookMention
    notify_on_success = [bool]$NotifyOnSuccess
    log_path = (Join-Path $scriptDir 'logs\r12_health_watch_task.jsonl')
    json_out_file = (Join-Path $scriptDir 'logs\r12_health_watch_status.latest.json')
    max_log_age_minutes = 30
    updated_at = [datetimeoffset]::Now.ToString('o')
}
($configPayload | ConvertTo-Json -Depth 6) | Set-Content -Path $ConfigFile -Encoding UTF8
Write-Host "[OK] Config written: $ConfigFile" -ForegroundColor Green

$createTask = {
    param([string]$Level)
    $args = @('/Create', '/SC', 'MINUTE', '/MO', "$IntervalMinutes", '/TN', $TaskName, '/TR', $taskRun, '/RL', $Level, '/F')
    if ($useSystemAccount) {
        $args += @('/RU', 'SYSTEM')
    }
    schtasks @args | Out-Null
    return $LASTEXITCODE
}

$exitCode = & $createTask $effectiveRunLevel
if ($exitCode -ne 0 -and $useSystemAccount -and -not $NoFallbackToCurrentUser) {
    Write-Host "[WARN] SYSTEM registration failed. retry with current user..." -ForegroundColor Yellow
    $useSystemAccount = $false
    if ($effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) {
        $effectiveRunLevel = 'LIMITED'
    }
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0 -and $effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited -and -not $useSystemAccount) {
    Write-Host "[WARN] HIGHEST registration failed. retry with LIMITED..." -ForegroundColor Yellow
    $effectiveRunLevel = 'LIMITED'
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0) {
    throw "Failed to create scheduled task (exit=$exitCode)"
}

Set-TaskBatteryPolicy -InTaskName $TaskName -Skip:$KeepBatteryRestrictions

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
Write-Host "[OK] Effective RunLevel: $effectiveRunLevel" -ForegroundColor Green
Write-Host "[OK] Effective Account : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}
