param(
    [string]$ConfigFile = "",
    [string]$StatusScript = "",
    [string]$JsonOutFile = "",
    [string]$SummaryLogPath = "",
    [int]$TailLines = 20,
    [int]$MaxR12LogAgeMinutes = 20,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [bool]$NotifyOnDegraded = $true,
    [int]$NotifyDegradedAfter = 3,
    [int]$NotifyDegradedCooldownMinutes = 60,
    [int]$NotifyFailureCooldownMinutes = 15,
    [string]$DegradedStateFile = "",
    [switch]$EnableAutoRecovery,
    [int]$RecoverAfterConsecutiveEndpointDown = 3,
    [int]$RecoveryCooldownMinutes = 10,
    [string]$RecoveryCommand = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function To-Bool {
    param(
        [object]$Value,
        [bool]$Default = $false
    )

    if ($null -eq $Value) { return $Default }
    if ($Value -is [bool]) { return [bool]$Value }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    if ($text -in @('1','true','yes','on','enabled')) { return $true }
    if ($text -in @('0','false','no','off','disabled')) { return $false }
    return $Default
}

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\r12_rl_ops_watch_task.config.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.status_script) { $StatusScript = [string]$cfg.status_script }
        if ($cfg.json_out_file) { $JsonOutFile = [string]$cfg.json_out_file }
        if ($cfg.summary_log_path) { $SummaryLogPath = [string]$cfg.summary_log_path }
        if ($null -ne $cfg.tail_lines) { $TailLines = [int]$cfg.tail_lines }
        if ($null -ne $cfg.max_r12_log_age_minutes) { $MaxR12LogAgeMinutes = [int]$cfg.max_r12_log_age_minutes }
        if ($cfg.webhook_format) { $WebhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_url) { $WebhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_mention) { $WebhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.notify_on_success) { $NotifyOnSuccess = To-Bool $cfg.notify_on_success }
        if ($null -ne $cfg.notify_on_degraded) { $NotifyOnDegraded = To-Bool $cfg.notify_on_degraded $true }
        if ($null -ne $cfg.notify_degraded_after) { $NotifyDegradedAfter = [int]$cfg.notify_degraded_after }
        if ($null -ne $cfg.notify_degraded_cooldown_minutes) { $NotifyDegradedCooldownMinutes = [int]$cfg.notify_degraded_cooldown_minutes }
        if ($null -ne $cfg.notify_failure_cooldown_minutes) { $NotifyFailureCooldownMinutes = [int]$cfg.notify_failure_cooldown_minutes }
        if ($cfg.degraded_state_file) { $DegradedStateFile = [string]$cfg.degraded_state_file }
        if ($null -ne $cfg.enable_auto_recovery) { $EnableAutoRecovery = To-Bool $cfg.enable_auto_recovery }
        if ($null -ne $cfg.recover_after_consecutive_endpoint_down) { $RecoverAfterConsecutiveEndpointDown = [int]$cfg.recover_after_consecutive_endpoint_down }
        if ($null -ne $cfg.recovery_cooldown_minutes) { $RecoveryCooldownMinutes = [int]$cfg.recovery_cooldown_minutes }
        if ($cfg.recovery_command) { $RecoveryCommand = [string]$cfg.recovery_command }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

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
if ($MaxR12LogAgeMinutes -lt 1) {
    $MaxR12LogAgeMinutes = 1
}
if ($RecoverAfterConsecutiveEndpointDown -lt 1) {
    $RecoverAfterConsecutiveEndpointDown = 1
}
if ($RecoveryCooldownMinutes -lt 0) {
    $RecoveryCooldownMinutes = 0
}
if ([string]::IsNullOrWhiteSpace($RecoveryCommand)) {
    $RecoveryCommand = "Set-Location '$scriptDir'; pwsh -NoProfile -ExecutionPolicy Bypass -File '.\\manaos-rpg\\scripts\\run_backend.ps1' -ForceKill"
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
            consecutive_endpoint_refused = 0
            last_degraded_notified_at = ''
            last_degraded_category = ''
            last_failure_notified_at = ''
            last_failure_category = ''
            last_recovery_at = ''
            last_ok = $true
        }
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            consecutive_unhealthy = 0
            consecutive_endpoint_refused = 0
            last_degraded_notified_at = ''
            last_degraded_category = ''
            last_failure_notified_at = ''
            last_failure_category = ''
            last_recovery_at = ''
            last_ok = $true
        }
    }
}

function Save-DegradedState {
    param(
        [string]$Path,
        [int]$ConsecutiveUnhealthy,
        [int]$ConsecutiveEndpointRefused,
        [string]$LastDegradedNotifiedAt,
        [string]$LastDegradedCategory,
        [string]$LastFailureNotifiedAt,
        [string]$LastFailureCategory,
        [string]$LastRecoveryAt,
        [bool]$LastOk
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{
        consecutive_unhealthy = $ConsecutiveUnhealthy
        consecutive_endpoint_refused = $ConsecutiveEndpointRefused
        last_degraded_notified_at = $LastDegradedNotifiedAt
        last_degraded_category = $LastDegradedCategory
        last_failure_notified_at = $LastFailureNotifiedAt
        last_failure_category = $LastFailureCategory
        last_recovery_at = $LastRecoveryAt
        last_ok = $LastOk
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Path -Encoding UTF8
}

function Test-IsConnectionRefused {
    param([string]$ErrorText)

    if ([string]::IsNullOrWhiteSpace($ErrorText)) {
        return $false
    }

    $text = $ErrorText.ToLowerInvariant()
    if ($text -like '*actively refused*') { return $true }
    if ($text -like '*connection refused*') { return $true }
    if ($ErrorText -like '*接続できませんでした*' -and $ErrorText -like '*拒否*') { return $true }
    return $false
}

function Invoke-R12AutoRecovery {
    param([string]$CommandText)

    $result = [ordered]@{
        attempted = $true
        started = $false
        command = $CommandText
        error = ''
        at = [datetimeoffset]::Now.ToString('o')
    }

    try {
        Start-Process -FilePath 'pwsh' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command',$CommandText) -WindowStyle Hidden | Out-Null
        $result.started = $true
    }
    catch {
        $result.error = $_.Exception.Message
    }

    return [pscustomobject]$result
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
if ($NotifyFailureCooldownMinutes -lt 0) { $NotifyFailureCooldownMinutes = 0 }

$statusOutput = & pwsh -NoProfile -ExecutionPolicy Bypass -File $StatusScript -Json -JsonOutFile $JsonOutFile -TailLines $TailLines -MaxR12LogAgeMinutes $MaxR12LogAgeMinutes 2>&1
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
    status_latest_ok = if ($null -ne $payload.latest_ok) { $payload.latest_ok } else { $payload.opsWatch.latestOk }
    status_latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$payload.latest_ok_reason)) { [string]$payload.latest_ok_reason } else { [string]$payload.opsWatch.latestOkReason }
    status_latest_failure_category = [string]$payload.latest_failure_category
    status_latest_failure_notify_attempted = $payload.latest_failure_notify_attempted
    status_latest_failure_notified = $payload.latest_failure_notified
    status_latest_failure_notify_suppressed_reason = [string]$payload.latest_failure_notify_suppressed_reason
    status_latest_degraded_notify_attempted = $payload.latest_degraded_notify_attempted
    status_latest_degraded_notified = $payload.latest_degraded_notified
    status_latest_degraded_notify_suppressed_reason = [string]$payload.latest_degraded_notify_suppressed_reason
    status_exit = $statusExit
    previous_last_ok = $true
    recovered_this_run = $false
    consecutive_unhealthy = 0
    consecutive_endpoint_refused = 0
    failure_category = ''
    failure_reason = ''
    auto_recovery_attempted = $false
    auto_recovery_started = $false
    auto_recovery_error = ''
    failure_notify_attempted = $false
    failure_notified = $false
    degraded_notify_attempted = $false
    degraded_notified = $false
    failure_notify_suppressed_reason = ''
    degraded_notify_suppressed_reason = ''
    issues = $issues
    status_json = $JsonOutFile
}

$degradedState = Load-DegradedState -Path $DegradedStateFile
$previousLastOk = $true
try { $previousLastOk = [bool]$degradedState.last_ok } catch { $previousLastOk = $true }
$summary.previous_last_ok = $previousLastOk

$consecutiveUnhealthy = 0
try { $consecutiveUnhealthy = [int]$degradedState.consecutive_unhealthy } catch { $consecutiveUnhealthy = 0 }
if ($ok) { $consecutiveUnhealthy = 0 } else { $consecutiveUnhealthy += 1 }
$summary.consecutive_unhealthy = $consecutiveUnhealthy

$consecutiveEndpointRefused = 0
try { $consecutiveEndpointRefused = [int]$degradedState.consecutive_endpoint_refused } catch { $consecutiveEndpointRefused = 0 }

$lastDegradedNotifiedAt = [string]$degradedState.last_degraded_notified_at
$lastDegradedNotifiedDt = $null
if (-not [string]::IsNullOrWhiteSpace($lastDegradedNotifiedAt)) {
    try { $lastDegradedNotifiedDt = [datetimeoffset]::Parse($lastDegradedNotifiedAt) } catch { $lastDegradedNotifiedDt = $null }
}
$lastDegradedCategory = [string]$degradedState.last_degraded_category

$lastFailureNotifiedAt = [string]$degradedState.last_failure_notified_at
$lastFailureNotifiedDt = $null
if (-not [string]::IsNullOrWhiteSpace($lastFailureNotifiedAt)) {
    try { $lastFailureNotifiedDt = [datetimeoffset]::Parse($lastFailureNotifiedAt) } catch { $lastFailureNotifiedDt = $null }
}
$lastFailureCategory = [string]$degradedState.last_failure_category

$lastRecoveryAt = [string]$degradedState.last_recovery_at
$lastRecoveryDt = $null
if (-not [string]::IsNullOrWhiteSpace($lastRecoveryAt)) {
    try { $lastRecoveryDt = [datetimeoffset]::Parse($lastRecoveryAt) } catch { $lastRecoveryDt = $null }
}

$summaryDir = Split-Path -Parent $SummaryLogPath
if ($summaryDir -and -not (Test-Path $summaryDir)) {
    New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null
}

if ($ok) {
    if (-not $previousLastOk) {
        $summary.recovered_this_run = $true
    }
    $line = "[OK] R12+RL ops healthy | r12=$r12State/$r12Result rl=$rlState/$rlResult latest_failed=$latestFailed"
    Write-Host $line -ForegroundColor Green
    if ($NotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'success' -Title '[R12+RL Ops] SUCCESS' -Body $line -Mention $WebhookMention
    }
    if ($Json.IsPresent) {
        Write-Output ($summary | ConvertTo-Json -Depth 6)
    }
    Save-DegradedState -Path $DegradedStateFile -ConsecutiveUnhealthy $consecutiveUnhealthy -ConsecutiveEndpointRefused 0 -LastDegradedNotifiedAt '' -LastDegradedCategory '' -LastFailureNotifiedAt '' -LastFailureCategory '' -LastRecoveryAt $lastRecoveryAt -LastOk $true
    ($summary | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $SummaryLogPath -Encoding UTF8
    exit 0
}

$classification = Get-FailureClassification -StatusPayload $payload -StatusExitCode $statusExit
$summary.failure_category = [string]$classification.category
$summary.failure_reason = [string]$classification.reason

$isEndpointRefused = $false
if ($classification.category -eq 'r12_endpoint' -and $null -ne $payload.r12Log -and $null -ne $payload.r12Log.latest) {
    $details = @($payload.r12Log.latest.details)
    foreach ($detail in $details) {
        if (Test-IsConnectionRefused -ErrorText ([string]$detail.error)) {
            $isEndpointRefused = $true
            break
        }
    }
}

if ($isEndpointRefused) {
    $consecutiveEndpointRefused += 1
}
else {
    $consecutiveEndpointRefused = 0
}
$summary.consecutive_endpoint_refused = $consecutiveEndpointRefused

$issueText = if ($issues.Count -gt 0) { ($issues -join '; ') } else { [string]$classification.reason }
$alertLine = "[ALERT] R12+RL ops unhealthy | category=$($classification.category) r12=$r12State/$r12Result rl=$rlState/$rlResult reason=$($classification.reason) issues=$issueText"
Write-Host $alertLine -ForegroundColor Red
if ($statusOutput) {
    Write-Host "=== status_r12_rl_ops.ps1 output (raw) ===" -ForegroundColor Yellow
    $statusOutput | ForEach-Object { Write-Host $_ }
}

if ([bool]$EnableAutoRecovery -and $isEndpointRefused -and $consecutiveEndpointRefused -ge $RecoverAfterConsecutiveEndpointDown) {
    $shouldRecover = $false
    if ($null -eq $lastRecoveryDt) {
        $shouldRecover = $true
    }
    elseif (([datetimeoffset]::Now - $lastRecoveryDt).TotalMinutes -ge $RecoveryCooldownMinutes) {
        $shouldRecover = $true
    }

    if ($shouldRecover) {
        $recovery = Invoke-R12AutoRecovery -CommandText $RecoveryCommand
        $summary.auto_recovery_attempted = $true
        $summary.auto_recovery_started = [bool]$recovery.started
        $summary.auto_recovery_error = [string]$recovery.error
        if ($recovery.started) {
            $lastRecoveryAt = [datetimeoffset]::Now.ToString('o')
            Write-Host "[WARN] R12 auto recovery started (endpoint refused streak=$consecutiveEndpointRefused)" -ForegroundColor Yellow
        }
        else {
            Write-Host "[WARN] R12 auto recovery failed: $($recovery.error)" -ForegroundColor Yellow
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $now = [datetimeoffset]::Now
    $summary.failure_notify_attempted = $true
    $shouldNotifyFailure = $false
    if ([string]::IsNullOrWhiteSpace($lastFailureCategory) -or $lastFailureCategory -ne [string]$classification.category) {
        $shouldNotifyFailure = $true
    }
    elseif ($null -eq $lastFailureNotifiedDt) {
        $shouldNotifyFailure = $true
    }
    else {
        $failureElapsedMinutes = ($now - $lastFailureNotifiedDt).TotalMinutes
        if ($failureElapsedMinutes -ge $NotifyFailureCooldownMinutes) {
            $shouldNotifyFailure = $true
        }
        else {
            $remainingFailureCooldown = [math]::Ceiling($NotifyFailureCooldownMinutes - $failureElapsedMinutes)
            $summary.failure_notify_suppressed_reason = "same_category_cooldown(${remainingFailureCooldown}m_remaining)"
        }
    }

    if ($shouldNotifyFailure) {
        $summary.failure_notify_suppressed_reason = ''
        $alertTitle = "[R12+RL Ops] FAILURE ($($classification.category))"
        Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'failure' -Title $alertTitle -Body $alertLine -Mention $WebhookMention
        $lastFailureNotifiedAt = $now.ToString('o')
        $lastFailureCategory = [string]$classification.category
        $summary.failure_notified = $true
    }
    elseif (-not [string]::IsNullOrWhiteSpace($summary.failure_notify_suppressed_reason)) {
        Write-Host "[INFO] Failure notification suppressed: $($summary.failure_notify_suppressed_reason)" -ForegroundColor DarkGray
    }
    elseif (-not $summary.failure_notified) {
        $summary.failure_notify_suppressed_reason = 'not_triggered'
    }

    if ($NotifyOnDegraded -and $consecutiveUnhealthy -ge $NotifyDegradedAfter) {
        $summary.degraded_notify_attempted = $true
        $shouldNotifyDegraded = $false
        if ([string]::IsNullOrWhiteSpace($lastDegradedCategory) -or $lastDegradedCategory -ne [string]$classification.category) {
            $shouldNotifyDegraded = $true
        }
        elseif ($null -eq $lastDegradedNotifiedDt) {
            $shouldNotifyDegraded = $true
        }
        else {
            $degradedElapsedMinutes = ($now - $lastDegradedNotifiedDt).TotalMinutes
            if ($degradedElapsedMinutes -ge $NotifyDegradedCooldownMinutes) {
                $shouldNotifyDegraded = $true
            }
            else {
                $remainingDegradedCooldown = [math]::Ceiling($NotifyDegradedCooldownMinutes - $degradedElapsedMinutes)
                $summary.degraded_notify_suppressed_reason = "same_category_cooldown(${remainingDegradedCooldown}m_remaining)"
            }
        }

        if ($shouldNotifyDegraded) {
            $summary.degraded_notify_suppressed_reason = ''
            $degradedTitle = "[R12+RL Ops] DEGRADED (unhealthy_streak)"
            $degradedBody = "$alertLine threshold=$NotifyDegradedAfter streak=$consecutiveUnhealthy"
            Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'warning' -Title $degradedTitle -Body $degradedBody -Mention $WebhookMention
            $lastDegradedNotifiedAt = $now.ToString('o')
            $lastDegradedCategory = [string]$classification.category
            $summary.degraded_notified = $true
        }
        elseif (-not [string]::IsNullOrWhiteSpace($summary.degraded_notify_suppressed_reason)) {
            Write-Host "[INFO] Degraded notification suppressed: $($summary.degraded_notify_suppressed_reason)" -ForegroundColor DarkGray
        }
        elseif (-not $summary.degraded_notified) {
            $summary.degraded_notify_suppressed_reason = 'not_triggered'
        }
    }
    elseif ($NotifyOnDegraded -and $consecutiveUnhealthy -lt $NotifyDegradedAfter) {
        $summary.degraded_notify_suppressed_reason = "below_threshold(streak=$consecutiveUnhealthy threshold=$NotifyDegradedAfter)"
    }
    elseif (-not $NotifyOnDegraded) {
        $summary.degraded_notify_suppressed_reason = 'disabled'
    }
}
else {
    $summary.failure_notify_suppressed_reason = 'webhook_not_configured'
    $summary.degraded_notify_suppressed_reason = 'webhook_not_configured'
}
if ($Json.IsPresent) {
    Write-Output ($summary | ConvertTo-Json -Depth 6)
}
Save-DegradedState -Path $DegradedStateFile -ConsecutiveUnhealthy $consecutiveUnhealthy -ConsecutiveEndpointRefused $consecutiveEndpointRefused -LastDegradedNotifiedAt $lastDegradedNotifiedAt -LastDegradedCategory $lastDegradedCategory -LastFailureNotifiedAt $lastFailureNotifiedAt -LastFailureCategory $lastFailureCategory -LastRecoveryAt $lastRecoveryAt -LastOk $false
($summary | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $SummaryLogPath -Encoding UTF8
exit 1
