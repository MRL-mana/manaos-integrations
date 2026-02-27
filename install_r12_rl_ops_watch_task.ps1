param(
    [string]$TaskName = "ManaOS_R12_RL_Ops_Watch_15min",
    [int]$IntervalMinutes = 15,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [switch]$DisableNotifyOnDegraded,
    [int]$NotifyDegradedAfter = 3,
    [int]$NotifyDegradedCooldownMinutes = 60,
    [string]$DegradedStateFile = "",
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$RunAsSystem,
    [switch]$KeepBatteryRestrictions,
    [switch]$NoFallbackToCurrentUser,
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "check_r12_rl_ops_watch_quick.ps1"
$jsonOut = Join-Path $scriptDir "logs\r12_rl_ops_status.latest.json"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}
if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw "IntervalMinutes must be 1..1440"
}
if ($NotifyDegradedAfter -lt 1) {
    throw "NotifyDegradedAfter must be >= 1"
}
if ($NotifyDegradedCooldownMinutes -lt 0) {
    throw "NotifyDegradedCooldownMinutes must be >= 0"
}
if ([string]::IsNullOrWhiteSpace($DegradedStateFile)) {
    $DegradedStateFile = Join-Path $scriptDir "logs\r12_rl_ops_watch_state.json"
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if (-not $NotifyOnSuccess.IsPresent -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
    $raw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
    if ($raw -in @('1','true','yes','on')) { $NotifyOnSuccess = $true }
}

$taskArgs = @(
    '-NoP',
    '-EP',
    'Bypass',
    '-File',
    "`"$jobScript`"",
    '-JsonOutFile',
    "`"$jsonOut`"",
    '-NotifyDegradedAfter',
    "$NotifyDegradedAfter",
    '-NotifyDegradedCooldownMinutes',
    "$NotifyDegradedCooldownMinutes",
    '-DegradedStateFile',
    "`"$DegradedStateFile`""
)

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
if ($DisableNotifyOnDegraded.IsPresent) {
    $taskArgs += '-NotifyOnDegraded:$false'
}

$taskRun = "pwsh " + ($taskArgs -join ' ')
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
    }
    catch {
        $msg = $_.Exception.Message
        if ($msg -match '0x8007007B') {
            Write-Host "[INFO] Battery policy update skipped (task remains valid): $msg" -ForegroundColor DarkGray
            return
        }
        Write-Host "[WARN] Failed to update battery policy: $msg" -ForegroundColor Yellow
    }
}

Write-Host "=== Register R12+RL Ops Watch Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $effectiveRunLevel" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Degraded : enabled=$(if ($DisableNotifyOnDegraded.IsPresent) { 'false' } else { 'true' }), after=$NotifyDegradedAfter, cooldown=${NotifyDegradedCooldownMinutes}min" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

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
