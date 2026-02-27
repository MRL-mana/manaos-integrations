param(
    [string]$StatusScript = "",
    [string]$JsonOutFile = "",
    [string]$SummaryLogPath = "",
    [int]$TailLines = 20,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [bool]$NotifyOnDegraded = $true,
    [int]$NotifyDegradedAfter = 3,
    [int]$NotifyDegradedCooldownMinutes = 60,
    [string]$DegradedStateFile = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($StatusScript)) {
    $StatusScript = Join-Path $scriptDir "status_r12_rl_ops.ps1"
}
if ([string]::IsNullOrWhiteSpace($JsonOutFile)) {
    $JsonOutFile = Join-Path $scriptDir "logs\r12_rl_ops_status.latest.json"
}
if ([string]::IsNullOrWhiteSpace($SummaryLogPath)) {
    $SummaryLogPath = Join-Path $scriptDir "logs\r12_rl_ops_watch.jsonl"
}
if ([string]::IsNullOrWhiteSpace($DegradedStateFile)) {
    $DegradedStateFile = Join-Path $scriptDir "logs\r12_rl_ops_watch_state.json"
}

if (-not (Test-Path $StatusScript)) {
    throw "Status script not found: $StatusScript"
}

function Resolve-NotifySettings {
    param(
        [string]$InWebhookUrl,
        [string]$InWebhookFormat,
        [string]$InWebhookMention,
        [bool]$InNotifyOnSuccess
    )

    $resolvedUrl = $InWebhookUrl
    if ([string]::IsNullOrWhiteSpace($resolvedUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
        $resolvedUrl = $env:MANAOS_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
        $resolvedUrl = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")
    }

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $envFormat
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User"))) {
        $userFormat = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User").Trim().ToLowerInvariant()
        if ($userFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $userFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $raw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($raw -in @("1", "true", "yes", "on"))
    }
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User"))) {
        $rawUser = [Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User").Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($rawUser -in @("1", "true", "yes", "on"))
    }

    $resolvedNotifyOnDegraded = $NotifyOnDegraded
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_R12RL_NOTIFY_ON_DEGRADED)) {
        $raw = $env:MANAOS_R12RL_NOTIFY_ON_DEGRADED.Trim().ToLowerInvariant()
        $resolvedNotifyOnDegraded = ($raw -in @("1", "true", "yes", "on"))
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_ON_DEGRADED", "User"))) {
        $rawUser = [Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_ON_DEGRADED", "User").Trim().ToLowerInvariant()
        $resolvedNotifyOnDegraded = ($rawUser -in @("1", "true", "yes", "on"))
    }

    $resolvedNotifyDegradedAfter = $NotifyDegradedAfter
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_R12RL_NOTIFY_DEGRADED_AFTER)) {
        try { $resolvedNotifyDegradedAfter = [int]$env:MANAOS_R12RL_NOTIFY_DEGRADED_AFTER } catch {}
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_DEGRADED_AFTER", "User"))) {
        try { $resolvedNotifyDegradedAfter = [int][Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_DEGRADED_AFTER", "User") } catch {}
    }

    $resolvedNotifyDegradedCooldownMinutes = $NotifyDegradedCooldownMinutes
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_R12RL_NOTIFY_DEGRADED_COOLDOWN_MINUTES)) {
        try { $resolvedNotifyDegradedCooldownMinutes = [int]$env:MANAOS_R12RL_NOTIFY_DEGRADED_COOLDOWN_MINUTES } catch {}
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_DEGRADED_COOLDOWN_MINUTES", "User"))) {
        try { $resolvedNotifyDegradedCooldownMinutes = [int][Environment]::GetEnvironmentVariable("MANAOS_R12RL_NOTIFY_DEGRADED_COOLDOWN_MINUTES", "User") } catch {}
    }

    return [pscustomobject]@{
        webhook_url = [string]$resolvedUrl
        webhook_format = [string]$resolvedFormat
        webhook_mention = [string]$resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
        notify_on_degraded = [bool]$resolvedNotifyOnDegraded
        notify_degraded_after = [int]$resolvedNotifyDegradedAfter
        notify_degraded_cooldown_minutes = [int]$resolvedNotifyDegradedCooldownMinutes
    }
}

function Load-DegradedState {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            consecutive_unhealthy = 0
            last_degraded_notified_at = ''
            last_ok = $true
        }
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            consecutive_unhealthy = 0
            last_degraded_notified_at = ''
            last_ok = $true
        }
    }
}

function Save-DegradedState {
    param(
        [string]$Path,
        [int]$ConsecutiveUnhealthy,
        [string]$LastDegradedNotifiedAt,
        [bool]$LastOk
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{
        consecutive_unhealthy = $ConsecutiveUnhealthy
        last_degraded_notified_at = $LastDegradedNotifiedAt
        last_ok = $LastOk
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Path -Encoding UTF8
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

    if ([string]::IsNullOrWhiteSpace($Url)) { return }

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
        Write-Host "[OK] Webhook notified ($Status)" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Webhook notify failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Get-FailureClassification {
    param(
        $StatusPayload,
        [int]$StatusExitCode
    )

    $r12Issues = @($StatusPayload.r12Task.issues)
    $rlIssues = @($StatusPayload.rlTask.issues)
    $logIssues = @($StatusPayload.r12Log.issues)
    $latestFailed = $null
    if ($null -ne $StatusPayload.r12Log -and $null -ne $StatusPayload.r12Log.latest) {
        $latestFailed = $StatusPayload.r12Log.latest.failed
    }

    if ($r12Issues.Count -gt 0) {
        return [pscustomobject]@{
            category = 'r12_task'
            reason = ($r12Issues -join '; ')
        }
    }
    if ($rlIssues.Count -gt 0) {
        return [pscustomobject]@{
            category = 'rl_task'
            reason = ($rlIssues -join '; ')
        }
    }
    if ($null -ne $latestFailed -and [int]$latestFailed -gt 0) {
        return [pscustomobject]@{
            category = 'r12_endpoint'
            reason = "r12 endpoints failed=$latestFailed"
        }
    }
    if ($logIssues.Count -gt 0) {
        return [pscustomobject]@{
            category = 'r12_log'
            reason = ($logIssues -join '; ')
        }
    }
    if ($StatusExitCode -ne 0) {
        return [pscustomobject]@{
            category = 'status_script'
            reason = "status script exit=$StatusExitCode"
        }
    }

    return [pscustomobject]@{
        category = 'unknown'
        reason = 'unknown issue'
    }
}

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success
$NotifyOnDegraded = [bool]$notify.notify_on_degraded
$NotifyDegradedAfter = [int]$notify.notify_degraded_after
$NotifyDegradedCooldownMinutes = [int]$notify.notify_degraded_cooldown_minutes

if ($NotifyDegradedAfter -lt 1) { $NotifyDegradedAfter = 1 }
if ($NotifyDegradedCooldownMinutes -lt 0) { $NotifyDegradedCooldownMinutes = 0 }

$statusOutput = & pwsh -NoProfile -ExecutionPolicy Bypass -File $StatusScript -Json -JsonOutFile $JsonOutFile -TailLines $TailLines 2>&1
$statusExit = $LASTEXITCODE

if (-not (Test-Path $JsonOutFile)) {
    throw "JSON output not found: $JsonOutFile"
}

$payload = Get-Content -Path $JsonOutFile -Raw | ConvertFrom-Json
$ok = [bool]$payload.ok
$issues = @($payload.issues)
$r12State = [string]$payload.r12Task.state
$r12Result = [string]$payload.r12Task.lastResult
$rlState = [string]$payload.rlTask.state
$rlResult = [string]$payload.rlTask.lastResult
$latestFailed = $null
if ($null -ne $payload.r12Log -and $null -ne $payload.r12Log.latest) {
    $latestFailed = $payload.r12Log.latest.failed
}

$summary = [pscustomobject]@{
    ts = [datetimeoffset]::Now.ToString('o')
    ok = $ok
    r12_state = $r12State
    r12_last_result = $r12Result
    rl_state = $rlState
    rl_last_result = $rlResult
    r12_latest_failed = $latestFailed
    ops_watch_last_result = [string]$payload.opsWatchTask.lastResult
    ops_watch_state = [string]$payload.opsWatchTask.state
    status_exit = $statusExit
    consecutive_unhealthy = 0
    failure_category = ''
    failure_reason = ''
    issues = $issues
    status_json = $JsonOutFile
}

$degradedState = Load-DegradedState -Path $DegradedStateFile
$consecutiveUnhealthy = 0
try { $consecutiveUnhealthy = [int]$degradedState.consecutive_unhealthy } catch { $consecutiveUnhealthy = 0 }
if ($ok) { $consecutiveUnhealthy = 0 } else { $consecutiveUnhealthy += 1 }
$summary.consecutive_unhealthy = $consecutiveUnhealthy

$lastDegradedNotifiedAt = [string]$degradedState.last_degraded_notified_at
$lastDegradedNotifiedDt = $null
if (-not [string]::IsNullOrWhiteSpace($lastDegradedNotifiedAt)) {
    try { $lastDegradedNotifiedDt = [datetimeoffset]::Parse($lastDegradedNotifiedAt) } catch { $lastDegradedNotifiedDt = $null }
}

$summaryDir = Split-Path -Parent $SummaryLogPath
if ($summaryDir -and -not (Test-Path $summaryDir)) {
    New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null
}

if ($ok) {
    $line = "[OK] R12+RL ops healthy | r12=$r12State/$r12Result rl=$rlState/$rlResult latest_failed=$latestFailed"
    Write-Host $line -ForegroundColor Green
    if ($NotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'success' -Title '[R12+RL Ops] SUCCESS' -Body $line -Mention $WebhookMention
    }
    if ($Json.IsPresent) {
        Write-Output ($summary | ConvertTo-Json -Depth 6)
    }
    Save-DegradedState -Path $DegradedStateFile -ConsecutiveUnhealthy $consecutiveUnhealthy -LastDegradedNotifiedAt $lastDegradedNotifiedAt -LastOk $true
    ($summary | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $SummaryLogPath -Encoding UTF8
    exit 0
}

$classification = Get-FailureClassification -StatusPayload $payload -StatusExitCode $statusExit
$summary.failure_category = [string]$classification.category
$summary.failure_reason = [string]$classification.reason

$issueText = if ($issues.Count -gt 0) { ($issues -join '; ') } else { [string]$classification.reason }
$alertLine = "[ALERT] R12+RL ops unhealthy | category=$($classification.category) r12=$r12State/$r12Result rl=$rlState/$rlResult reason=$($classification.reason) issues=$issueText"
Write-Host $alertLine -ForegroundColor Red
if ($statusOutput) {
    Write-Host "=== status_r12_rl_ops.ps1 output (raw) ===" -ForegroundColor Yellow
    $statusOutput | ForEach-Object { Write-Host $_ }
}
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $alertTitle = "[R12+RL Ops] FAILURE ($($classification.category))"
    Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'failure' -Title $alertTitle -Body $alertLine -Mention $WebhookMention

    if ($NotifyOnDegraded -and $consecutiveUnhealthy -ge $NotifyDegradedAfter) {
        $shouldNotifyDegraded = $false
        if ($null -eq $lastDegradedNotifiedDt) {
            $shouldNotifyDegraded = $true
        }
        elseif (([datetimeoffset]::Now - $lastDegradedNotifiedDt).TotalMinutes -ge $NotifyDegradedCooldownMinutes) {
            $shouldNotifyDegraded = $true
        }

        if ($shouldNotifyDegraded) {
            $degradedTitle = "[R12+RL Ops] DEGRADED (unhealthy_streak)"
            $degradedBody = "$alertLine threshold=$NotifyDegradedAfter streak=$consecutiveUnhealthy"
            Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'warning' -Title $degradedTitle -Body $degradedBody -Mention $WebhookMention
            $lastDegradedNotifiedAt = [datetimeoffset]::Now.ToString('o')
        }
    }
}
if ($Json.IsPresent) {
    Write-Output ($summary | ConvertTo-Json -Depth 6)
}
Save-DegradedState -Path $DegradedStateFile -ConsecutiveUnhealthy $consecutiveUnhealthy -LastDegradedNotifiedAt $lastDegradedNotifiedAt -LastOk $false
($summary | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $SummaryLogPath -Encoding UTF8
exit 1
