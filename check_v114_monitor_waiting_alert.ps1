param(
    [string]$ConfigFile = "",
    [string]$SummaryFile = "",
    [int]$Checkpoint = 4500,
    [int]$WaitingAlertMinutes = 30,
    [int]$NotifyCooldownMinutes = 60,
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
        if ($cfg.summary_file) { $SummaryFile = [string]$cfg.summary_file }
        if ($cfg.checkpoint) { $Checkpoint = [int]$cfg.checkpoint }
        if ($cfg.waiting_alert_minutes) { $WaitingAlertMinutes = [int]$cfg.waiting_alert_minutes }
        if ($cfg.notify_cooldown_minutes -or $cfg.notify_cooldown_minutes -eq 0) { $NotifyCooldownMinutes = [int]$cfg.notify_cooldown_minutes }
        if ($cfg.state_file) { $StateFile = [string]$cfg.state_file }
        if ($cfg.webhook_format) { $WebhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_url) { $WebhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_mention) { $WebhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.refresh_summary) { $RefreshSummary = [bool]$cfg.refresh_summary }
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
            updated_at = ''
        }
    }
}

function Save-State {
    param(
        [string]$Path,
        [string]$LastAlertAt,
        [string]$LastStatus,
        [object]$LastAlertedAgeSec
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{
        last_alert_at = $LastAlertAt
        last_status = $LastStatus
        last_alerted_age_sec = $LastAlertedAgeSec
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Path -Encoding UTF8
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

$ageSec = if ($null -ne $cp.age_sec) { [int]$cp.age_sec } else { 0 }
$status = [string]$cp.status
$shouldAlert = ($status -eq 'waiting' -and $ageSec -ge ($WaitingAlertMinutes * 60))

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
if ($shouldAlert -and $canNotify) {
    $notificationAttempted = $true
    $title = "[v114] ck$Checkpoint waiting alert"
    $body = "status=$status age_sec=$ageSec threshold_sec=$($WaitingAlertMinutes * 60) overall=$($summary.overall)"
    $notified = Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'degraded' -Title $title -Body $body -Mention $WebhookMention

    Save-State -Path $StateFile -LastAlertAt $now.ToString('o') -LastStatus $status -LastAlertedAgeSec $ageSec
}
else {
    Save-State -Path $StateFile -LastAlertAt ([string]$state.last_alert_at) -LastStatus $status -LastAlertedAgeSec $state.last_alerted_age_sec
}

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

exit 0
