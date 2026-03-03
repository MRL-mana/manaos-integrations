param(
    [string]$ConfigFile = "",
    [string]$SummaryFile = "",
    [int]$Checkpoint = 4500,
    [int]$WaitingAlertMinutes = 30,
    [int]$NotifyCooldownMinutes = 60,
    [switch]$EnableAutoRecovery,
    [int]$RecoverAfterConsecutiveAlerts = 3,
    [int]$RecoveryCooldownMinutes = 120,
    [string]$RecoveryCommand = "",
    [string]$RecoveryHistoryPath = "",
    [string]$StateFile = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$RefreshSummary,
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir 'logs\v114_waiting_alert_task.config.json'
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.summary_file -and -not $PSBoundParameters.ContainsKey('SummaryFile')) { $SummaryFile = [string]$cfg.summary_file }
        if ($cfg.checkpoint -and -not $PSBoundParameters.ContainsKey('Checkpoint')) { $Checkpoint = [int]$cfg.checkpoint }
        if ($cfg.waiting_alert_minutes -and -not $PSBoundParameters.ContainsKey('WaitingAlertMinutes')) { $WaitingAlertMinutes = [int]$cfg.waiting_alert_minutes }
        if (($cfg.notify_cooldown_minutes -or $cfg.notify_cooldown_minutes -eq 0) -and -not $PSBoundParameters.ContainsKey('NotifyCooldownMinutes')) { $NotifyCooldownMinutes = [int]$cfg.notify_cooldown_minutes }
        if ($null -ne $cfg.enable_auto_recovery -and -not $PSBoundParameters.ContainsKey('EnableAutoRecovery')) { $EnableAutoRecovery = [bool]$cfg.enable_auto_recovery }
        if ($cfg.recover_after_consecutive_alerts -and -not $PSBoundParameters.ContainsKey('RecoverAfterConsecutiveAlerts')) { $RecoverAfterConsecutiveAlerts = [int]$cfg.recover_after_consecutive_alerts }
        if (($cfg.recovery_cooldown_minutes -or $cfg.recovery_cooldown_minutes -eq 0) -and -not $PSBoundParameters.ContainsKey('RecoveryCooldownMinutes')) { $RecoveryCooldownMinutes = [int]$cfg.recovery_cooldown_minutes }
        if ($cfg.recovery_command -and -not $PSBoundParameters.ContainsKey('RecoveryCommand')) { $RecoveryCommand = [string]$cfg.recovery_command }
        if ($cfg.recovery_history_path -and -not $PSBoundParameters.ContainsKey('RecoveryHistoryPath')) { $RecoveryHistoryPath = [string]$cfg.recovery_history_path }
        if ($cfg.state_file -and -not $PSBoundParameters.ContainsKey('StateFile')) { $StateFile = [string]$cfg.state_file }
        if ($cfg.webhook_format -and -not $PSBoundParameters.ContainsKey('WebhookFormat')) { $WebhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_url -and -not $PSBoundParameters.ContainsKey('WebhookUrl')) { $WebhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_mention -and -not $PSBoundParameters.ContainsKey('WebhookMention')) { $WebhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.refresh_summary -and -not $PSBoundParameters.ContainsKey('RefreshSummary')) { $RefreshSummary = [bool]$cfg.refresh_summary }
    }
    catch {
    }
}

if ([string]::IsNullOrWhiteSpace($SummaryFile)) {
    $SummaryFile = Join-Path $scriptDir 'logs\v114_monitor_summary_latest.json'
}
if ([string]::IsNullOrWhiteSpace($StateFile)) {
    $StateFile = Join-Path $scriptDir 'logs\v114_waiting_alert_state.json'
}
if ($WaitingAlertMinutes -lt 1) { $WaitingAlertMinutes = 1 }
if ($NotifyCooldownMinutes -lt 0) { $NotifyCooldownMinutes = 0 }
if ($RecoverAfterConsecutiveAlerts -lt 1) { $RecoverAfterConsecutiveAlerts = 1 }
if ($RecoveryCooldownMinutes -lt 0) { $RecoveryCooldownMinutes = 0 }
if ([string]::IsNullOrWhiteSpace($RecoveryCommand)) {
    $RecoveryCommand = "Set-Location '$scriptDir'; powershell -ExecutionPolicy Bypass -File '.\\run_v114_onebutton.ps1' -SkipDataGen"
}
if ([string]::IsNullOrWhiteSpace($RecoveryHistoryPath)) {
    $RecoveryHistoryPath = Join-Path $scriptDir 'logs\v114_waiting_recovery_history.jsonl'
}

function Resolve-NotifySettings {
    param(
        [string]$InWebhookUrl,
        [string]$InWebhookFormat,
        [string]$InWebhookMention
    )

    $resolvedUrl = $InWebhookUrl
    if ([string]::IsNullOrWhiteSpace($resolvedUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
        $resolvedUrl = $env:MANAOS_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
        $resolvedUrl = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_URL', 'User')
    }

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @('generic', 'slack', 'discord')) {
            $resolvedFormat = $envFormat
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_FORMAT', 'User'))) {
        $userFormat = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_FORMAT', 'User').Trim().ToLowerInvariant()
        if ($userFormat -in @('generic', 'slack', 'discord')) {
            $resolvedFormat = $userFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }

    return [pscustomobject]@{
        webhook_url = [string]$resolvedUrl
        webhook_format = [string]$resolvedFormat
        webhook_mention = [string]$resolvedMention
    }
}

function Send-WebhookNotification {
    param(
        [string]$Url,
        [ValidateSet('generic','slack','discord')]
        [string]$Format,
        [string]$Status,
        [string]$Title,
        [string]$Body,
        [string]$Mention = ''
    )

    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }

    $content = if ([string]::IsNullOrWhiteSpace($Mention)) { "$Title`n$Body" } else { "$Mention $Title`n$Body" }
    if ($Format -eq 'discord') {
        $payload = @{ content = $content }
    }
    elseif ($Format -eq 'slack') {
        $payload = @{ text = $content }
    }
    else {
        $payload = @{ status = $Status; title = $Title; body = $Body; mention = $Mention }
    }

    try {
        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 8) | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Load-State {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            last_alert_at = ''
            last_status = ''
            last_alerted_age_sec = $null
            consecutive_waiting_alerts = 0
            last_recovery_at = ''
            last_recovery_started = $false
            last_recovery_error = ''
            updated_at = ''
        }
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            last_alert_at = ''
            last_status = ''
            last_alerted_age_sec = $null
            consecutive_waiting_alerts = 0
            last_recovery_at = ''
            last_recovery_started = $false
            last_recovery_error = ''
            updated_at = ''
        }
    }
}

function Save-State {
    param(
        [string]$Path,
        [string]$LastAlertAt,
        [string]$LastStatus,
        [object]$LastAlertedAgeSec,
        [int]$ConsecutiveWaitingAlerts,
        [string]$LastRecoveryAt,
        [bool]$LastRecoveryStarted,
        [string]$LastRecoveryError
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{
        last_alert_at = $LastAlertAt
        last_status = $LastStatus
        last_alerted_age_sec = $LastAlertedAgeSec
        consecutive_waiting_alerts = $ConsecutiveWaitingAlerts
        last_recovery_at = $LastRecoveryAt
        last_recovery_started = $LastRecoveryStarted
        last_recovery_error = $LastRecoveryError
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Path -Encoding UTF8
}

function Invoke-AutoRecovery {
    param([string]$CommandText)

    $started = $false
    $error = ''
    try {
        Start-Process -FilePath 'powershell' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $CommandText) -WindowStyle Hidden | Out-Null
        $started = $true
    }
    catch {
        $error = $_.Exception.Message
    }

    return [pscustomobject]@{
        started = $started
        error = $error
    }
}

function Append-RecoveryHistory {
    param(
        [string]$Path,
        [hashtable]$Entry
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    ($Entry | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $Path -Encoding UTF8
}

if ($RefreshSummary) {
    $summaryScript = Join-Path $scriptDir 'summarize_v114_monitor_logs.ps1'
    if (Test-Path $summaryScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $summaryScript -AsJson | Out-Null
    }
}

if (-not (Test-Path $SummaryFile)) {
    throw "summary file not found: $SummaryFile"
}

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention

$summary = Get-Content -Path $SummaryFile -Raw | ConvertFrom-Json
$checkpointRow = @($summary.checkpoints | Where-Object { [int]$_.checkpoint -eq $Checkpoint } | Select-Object -First 1)
if ($checkpointRow.Count -eq 0) {
    throw "checkpoint not found in summary: ck$Checkpoint"
}
$cp = $checkpointRow[0]

$state = Load-State -Path $StateFile
$now = [datetimeoffset]::Now
$lastAlertAt = $null
if (-not [string]::IsNullOrWhiteSpace([string]$state.last_alert_at)) {
    try { $lastAlertAt = [datetimeoffset]::Parse([string]$state.last_alert_at) } catch { $lastAlertAt = $null }
}
$lastRecoveryAt = $null
if (-not [string]::IsNullOrWhiteSpace([string]$state.last_recovery_at)) {
    try { $lastRecoveryAt = [datetimeoffset]::Parse([string]$state.last_recovery_at) } catch { $lastRecoveryAt = $null }
}

$ageSec = if ($null -ne $cp.age_sec) { [int]$cp.age_sec } else { 0 }
$status = [string]$cp.status
$shouldAlert = ($status -eq 'waiting' -and $ageSec -ge ($WaitingAlertMinutes * 60))
$consecutiveWaitingAlerts = 0
if ($null -ne $state.consecutive_waiting_alerts) {
    $consecutiveWaitingAlerts = [int]$state.consecutive_waiting_alerts
}
if ($shouldAlert) {
    $consecutiveWaitingAlerts += 1
}
else {
    $consecutiveWaitingAlerts = 0
}

$cooldownRemainingSec = 0
$canNotify = $true
if ($shouldAlert -and $NotifyCooldownMinutes -gt 0 -and $null -ne $lastAlertAt) {
    $elapsed = ($now - $lastAlertAt).TotalSeconds
    if ($elapsed -lt ($NotifyCooldownMinutes * 60)) {
        $canNotify = $false
        $cooldownRemainingSec = [int][Math]::Ceiling(($NotifyCooldownMinutes * 60) - $elapsed)
    }
}

$notified = $false
$notificationAttempted = $false
$recoveryAttempted = $false
$recoveryStarted = $false
$recoveryError = [string]$state.last_recovery_error
$recoveryCooldownRemainingSec = 0
$recoveryCanRun = $true
$recoveryHistoryWritten = $false
if ($EnableAutoRecovery -and $RecoveryCooldownMinutes -gt 0 -and $null -ne $lastRecoveryAt) {
    $recoveryElapsed = ($now - $lastRecoveryAt).TotalSeconds
    if ($recoveryElapsed -lt ($RecoveryCooldownMinutes * 60)) {
        $recoveryCanRun = $false
        $recoveryCooldownRemainingSec = [int][Math]::Ceiling(($RecoveryCooldownMinutes * 60) - $recoveryElapsed)
    }
}

if ($shouldAlert -and $canNotify) {
    $notificationAttempted = $true
    $title = "[v114] ck$Checkpoint waiting alert"
    $body = "status=$status age_sec=$ageSec threshold_sec=$($WaitingAlertMinutes * 60) overall=$($summary.overall)"
    $notified = Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'degraded' -Title $title -Body $body -Mention $WebhookMention
}

if ($EnableAutoRecovery -and $shouldAlert -and $consecutiveWaitingAlerts -ge $RecoverAfterConsecutiveAlerts -and $recoveryCanRun) {
    $recoveryAttempted = $true
    $recovery = Invoke-AutoRecovery -CommandText $RecoveryCommand
    $recoveryStarted = [bool]$recovery.started
    $recoveryError = [string]$recovery.error
    $lastRecoveryAt = $now

    $historyEntry = [ordered]@{
        ts = $now.ToString('o')
        checkpoint = [int]$Checkpoint
        status = $status
        age_sec = $ageSec
        waiting_alert_minutes = [int]$WaitingAlertMinutes
        consecutive_waiting_alerts = [int]$consecutiveWaitingAlerts
        auto_recovery_threshold = [int]$RecoverAfterConsecutiveAlerts
        recovery_started = [bool]$recoveryStarted
        recovery_error = [string]$recoveryError
        recovery_command = [string]$RecoveryCommand
        summary_overall = [string]$summary.overall
    }
    Append-RecoveryHistory -Path $RecoveryHistoryPath -Entry $historyEntry
    $recoveryHistoryWritten = $true
}

$effectiveLastAlertAt = [string]$state.last_alert_at
$effectiveLastAlertedAgeSec = $state.last_alerted_age_sec
if ($shouldAlert -and $canNotify) {
    $effectiveLastAlertAt = $now.ToString('o')
    $effectiveLastAlertedAgeSec = $ageSec
}

Save-State -Path $StateFile `
    -LastAlertAt $effectiveLastAlertAt `
    -LastStatus $status `
    -LastAlertedAgeSec $effectiveLastAlertedAgeSec `
    -ConsecutiveWaitingAlerts $consecutiveWaitingAlerts `
    -LastRecoveryAt $(if ($null -ne $lastRecoveryAt) { $lastRecoveryAt.ToString('o') } else { [string]$state.last_recovery_at }) `
    -LastRecoveryStarted $recoveryStarted `
    -LastRecoveryError $recoveryError

$result = [ordered]@{
    ts = $now.ToString('o')
    checkpoint = [int]$Checkpoint
    status = $status
    age_sec = $ageSec
    waiting_alert_minutes = [int]$WaitingAlertMinutes
    should_alert = [bool]$shouldAlert
    can_notify = [bool]$canNotify
    cooldown_remaining_sec = [int]$cooldownRemainingSec
    notification_attempted = [bool]$notificationAttempted
    notified = [bool]$notified
    consecutive_waiting_alerts = [int]$consecutiveWaitingAlerts
    auto_recovery_enabled = [bool]$EnableAutoRecovery
    auto_recovery_threshold = [int]$RecoverAfterConsecutiveAlerts
    recovery_attempted = [bool]$recoveryAttempted
    recovery_started = [bool]$recoveryStarted
    recovery_cooldown_remaining_sec = [int]$recoveryCooldownRemainingSec
    recovery_error = [string]$recoveryError
    recovery_history_path = [string]$RecoveryHistoryPath
    recovery_history_written = [bool]$recoveryHistoryWritten
    summary_file = $SummaryFile
    state_file = $StateFile
    webhook_format = $WebhookFormat
    webhook_configured = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    overall = [string]$summary.overall
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host '=== v114 waiting alert check ===' -ForegroundColor Cyan
Write-Host "checkpoint : ck$Checkpoint" -ForegroundColor Gray
Write-Host "status     : $status" -ForegroundColor Gray
Write-Host "age_sec    : $ageSec" -ForegroundColor Gray
Write-Host "threshold  : $($WaitingAlertMinutes * 60)s" -ForegroundColor Gray
Write-Host "shouldAlert: $shouldAlert" -ForegroundColor Gray
Write-Host "canNotify  : $canNotify" -ForegroundColor Gray
Write-Host "notified   : $notified" -ForegroundColor Gray
Write-Host "autoRecover: enabled=$EnableAutoRecovery attempted=$recoveryAttempted started=$recoveryStarted" -ForegroundColor Gray

exit 0
