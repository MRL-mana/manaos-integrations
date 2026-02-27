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

    return [pscustomobject]@{
        webhook_url = [string]$resolvedUrl
        webhook_format = [string]$resolvedFormat
        webhook_mention = [string]$resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
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

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

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
    status_exit = $statusExit
    issues = $issues
    status_json = $JsonOutFile
}

$summaryDir = Split-Path -Parent $SummaryLogPath
if ($summaryDir -and -not (Test-Path $summaryDir)) {
    New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null
}
($summary | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $SummaryLogPath -Encoding UTF8

if ($ok) {
    $line = "[OK] R12+RL ops healthy | r12=$r12State/$r12Result rl=$rlState/$rlResult latest_failed=$latestFailed"
    Write-Host $line -ForegroundColor Green
    if ($NotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'success' -Title '[R12+RL Ops] SUCCESS' -Body $line -Mention $WebhookMention
    }
    if ($Json.IsPresent) {
        Write-Output ($summary | ConvertTo-Json -Depth 6)
    }
    exit 0
}

$issueText = if ($issues.Count -gt 0) { ($issues -join '; ') } else { 'unknown issue' }
$alertLine = "[ALERT] R12+RL ops unhealthy | r12=$r12State/$r12Result rl=$rlState/$rlResult issues=$issueText"
Write-Host $alertLine -ForegroundColor Red
if ($statusOutput) {
    Write-Host "=== status_r12_rl_ops.ps1 output (raw) ===" -ForegroundColor Yellow
    $statusOutput | ForEach-Object { Write-Host $_ }
}
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'failure' -Title '[R12+RL Ops] FAILURE' -Body $alertLine -Mention $WebhookMention
}
if ($Json.IsPresent) {
    Write-Output ($summary | ConvertTo-Json -Depth 6)
}
exit 1
