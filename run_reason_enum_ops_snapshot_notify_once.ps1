param(
    [string]$ConfigFile = "",
    [string]$SnapshotScript = "",
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [int]$NotifyFailureCooldownMinutes = 60,
    [string]$NotifyStateFile = "",
    [switch]$SimulateFailure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot_notify.config.json"
}
if ([string]::IsNullOrWhiteSpace($SnapshotScript)) {
    $SnapshotScript = Join-Path $scriptDir "export_reason_enum_ops_snapshot.ps1"
}
if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot_notify.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\reason_enum_ops_snapshot_notify.history.jsonl"
}
if ([string]::IsNullOrWhiteSpace($NotifyStateFile)) {
    $NotifyStateFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot_notify_state.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.snapshot_script -and -not $PSBoundParameters.ContainsKey('SnapshotScript')) { $SnapshotScript = [string]$cfg.snapshot_script }
        if ($cfg.latest_json_file -and -not $PSBoundParameters.ContainsKey('LatestJsonFile')) { $LatestJsonFile = [string]$cfg.latest_json_file }
        if ($cfg.history_jsonl -and -not $PSBoundParameters.ContainsKey('HistoryJsonl')) { $HistoryJsonl = [string]$cfg.history_jsonl }
        if ($cfg.webhook_format -and -not $PSBoundParameters.ContainsKey('WebhookFormat')) { $WebhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_url -and -not $PSBoundParameters.ContainsKey('WebhookUrl')) { $WebhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_mention -and -not $PSBoundParameters.ContainsKey('WebhookMention')) { $WebhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.notify_failure_cooldown_minutes -and -not $PSBoundParameters.ContainsKey('NotifyFailureCooldownMinutes')) { $NotifyFailureCooldownMinutes = [int]$cfg.notify_failure_cooldown_minutes }
        if ($cfg.notify_state_file -and -not $PSBoundParameters.ContainsKey('NotifyStateFile')) { $NotifyStateFile = [string]$cfg.notify_state_file }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if ($NotifyFailureCooldownMinutes -lt 0) {
    $NotifyFailureCooldownMinutes = 0
}

function Send-WebhookMessage {
    param(
        [string]$Url,
        [string]$Format,
        [string]$Message,
        [string]$Mention
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $false
    }

    $text = if ([string]::IsNullOrWhiteSpace($Mention)) { $Message } else { "$Mention`n$Message" }
    $fmt = if ([string]::IsNullOrWhiteSpace($Format)) { 'discord' } else { $Format.Trim().ToLowerInvariant() }
    $payload = switch ($fmt) {
        'slack' { @{ text = $text } }
        'generic' { @{ text = $text } }
        default { @{ content = $text } }
    }

    try {
        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 6) | Out-Null
        return $true
    }
    catch {
        Write-Host "[WARN] Failed to send webhook: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

function Load-NotifyState {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            last_failure_notified_at = ''
            last_status = 'unknown'
        }
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            last_failure_notified_at = ''
            last_status = 'unknown'
        }
    }
}

function Save-NotifyState {
    param(
        [string]$Path,
        [string]$LastFailureNotifiedAt,
        [string]$LastStatus
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{
        last_failure_notified_at = $LastFailureNotifiedAt
        last_status = $LastStatus
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 4) | Set-Content -Path $Path -Encoding UTF8
}

if (-not (Test-Path $SnapshotScript)) {
    throw "Snapshot script not found: $SnapshotScript"
}

$latestDir = Split-Path -Parent $LatestJsonFile
if ($latestDir -and -not (Test-Path $latestDir)) {
    New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
}
$historyDir = Split-Path -Parent $HistoryJsonl
if ($historyDir -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
}

$runTs = [datetimeoffset]::Now.ToString('o')
$outputLines = @()
$exitCode = 999
$ok = $false
$okReason = 'snapshot_error'
$failureCategory = ''
$failureNotifyAttempted = $false
$failureNotified = $false
$failureNotifySuppressedReason = ''
$webhookEnabled = -not [string]::IsNullOrWhiteSpace($WebhookUrl)

if ($SimulateFailure.IsPresent) {
    $outputLines = @('[SIMULATED] ops snapshot forced failure for notification test')
    $exitCode = 2
    $ok = $false
    $okReason = 'snapshot_failed'
}
else {
    try {
        $cmdArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$SnapshotScript,'-AsJson')
        $outputLines = @(& pwsh @cmdArgs 2>&1 | ForEach-Object { [string]$_ })
        $exitCode = [int]$LASTEXITCODE
        $jsonText = ($outputLines -join [Environment]::NewLine)
        $startIndex = $jsonText.IndexOf('{')
        $endIndex = $jsonText.LastIndexOf('}')
        if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
            $jsonText = $jsonText.Substring($startIndex, ($endIndex - $startIndex + 1))
        }
        $snapshot = $jsonText | ConvertFrom-Json
        $ok = if ($null -ne $snapshot.ok) { [bool]$snapshot.ok } else { ($exitCode -eq 0) }
        $okReason = if (-not [string]::IsNullOrWhiteSpace([string]$snapshot.ok_reason)) { [string]$snapshot.ok_reason } else { if ($ok) { 'snapshot_passed' } else { 'snapshot_failed' } }
    }
    catch {
        $exitCode = if ($exitCode -eq 999) { 999 } else { $exitCode }
        $ok = $false
        $okReason = 'snapshot_error'
        $outputLines += $_.Exception.Message
    }
}

$outputTail = @($outputLines | Select-Object -Last 20)

if (-not $ok) {
    $failureCategory = 'ops_snapshot_failed'
    $failureNotifyAttempted = $true

    if (-not $webhookEnabled) {
        $failureNotifySuppressedReason = 'webhook_not_configured'
    }
    else {
        $state = Load-NotifyState -Path $NotifyStateFile
        $lastNotifiedAtRaw = [string]$state.last_failure_notified_at
        $canNotify = $true

        if (-not [string]::IsNullOrWhiteSpace($lastNotifiedAtRaw) -and $NotifyFailureCooldownMinutes -gt 0) {
            try {
                $lastNotifiedAt = [datetimeoffset]::Parse($lastNotifiedAtRaw)
                $elapsedMinutes = ([datetimeoffset]::Now - $lastNotifiedAt).TotalMinutes
                if ($elapsedMinutes -lt $NotifyFailureCooldownMinutes) {
                    $canNotify = $false
                    $remaining = [math]::Ceiling($NotifyFailureCooldownMinutes - $elapsedMinutes)
                    $failureNotifySuppressedReason = "same_category_cooldown(${remaining}m_remaining)"
                }
            }
            catch {
                $canNotify = $true
            }
        }

        if ($canNotify) {
            $lines = @(
                "[ALERT] ops snapshot failed",
                "exit_code=$exitCode",
                "ok_reason=$okReason",
                "snapshot_script=$SnapshotScript"
            ) + @($outputTail | Select-Object -First 8)
            $msg = ($lines -join "`n")
            $failureNotified = Send-WebhookMessage -Url $WebhookUrl -Format $WebhookFormat -Message $msg -Mention $WebhookMention
            if (-not $failureNotified -and [string]::IsNullOrWhiteSpace($failureNotifySuppressedReason)) {
                $failureNotifySuppressedReason = 'notify_send_failed'
            }
        }

        if ($failureNotified) {
            Save-NotifyState -Path $NotifyStateFile -LastFailureNotifiedAt ([datetimeoffset]::Now.ToString('o')) -LastStatus 'failure'
        }
        else {
            Save-NotifyState -Path $NotifyStateFile -LastFailureNotifiedAt $lastNotifiedAtRaw -LastStatus 'failure'
        }
    }
}
else {
    $state = Load-NotifyState -Path $NotifyStateFile
    Save-NotifyState -Path $NotifyStateFile -LastFailureNotifiedAt ([string]$state.last_failure_notified_at) -LastStatus 'ok'
}

$payload = [ordered]@{
    ts = $runTs
    ok = $ok
    ok_reason = $okReason
    failure_category = $failureCategory
    failure_notify_attempted = $failureNotifyAttempted
    failure_notified = $failureNotified
    failure_notify_suppressed_reason = $failureNotifySuppressedReason
    exit_code = [int]$exitCode
    snapshot_script = $SnapshotScript
    config_file = $ConfigFile
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    webhook_enabled = $webhookEnabled
    webhook_format = $WebhookFormat
    notify_failure_cooldown_minutes = [int]$NotifyFailureCooldownMinutes
    notify_state_file = $NotifyStateFile
    output_tail = $outputTail
}

($payload | ConvertTo-Json -Depth 8) | Set-Content -Path $LatestJsonFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8

if ($ok) {
    Write-Host "[OK] ops snapshot notify check passed" -ForegroundColor Green
}
else {
    Write-Host "[ALERT] ops snapshot notify check failed (exit=$exitCode)" -ForegroundColor Red
}

$outputTail | ForEach-Object { Write-Host $_ }
exit $exitCode
