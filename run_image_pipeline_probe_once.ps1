param(
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$probeScript = Join-Path $scriptDir "monitor_image_pipeline.ps1"

if (-not (Test-Path $probeScript)) {
    throw "Probe script not found: $probeScript"
}

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\image_pipeline_probe_task.config.json"
}

$unifiedApiUrl = "http://127.0.0.1:9502"
$comfyUiUrl = "http://127.0.0.1:8188"
$logFile = Join-Path $scriptDir "logs\image_pipeline_probe.latest.json"
$webhookUrl = ""
$webhookFormat = "discord"
$webhookMention = ""
$notifyOnSuccess = $false
$notifyCooldownMinutes = 15
$notifyStateFile = Join-Path $scriptDir "logs\image_pipeline_probe_notify_state.json"

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

function Load-NotifyState {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            last_status = ''
            last_notified_at = ''
            last_category = ''
        }
    }

    try {
        return (Get-Content -Path $Path -Raw | ConvertFrom-Json)
    }
    catch {
        Write-Host "[WARN] Failed to parse notify state file: $Path" -ForegroundColor Yellow
        return [pscustomobject]@{
            last_status = ''
            last_notified_at = ''
            last_category = ''
        }
    }
}

function Save-NotifyState {
    param(
        [string]$Path,
        [string]$Status,
        [string]$Category,
        [switch]$MarkNotified
    )

    $stateDir = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($stateDir) -and -not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }

    $obj = [ordered]@{
        last_status = $Status
        last_category = $Category
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    if ($MarkNotified.IsPresent) {
        $obj.last_notified_at = [datetimeoffset]::Now.ToString('o')
    }
    else {
        $existing = Load-NotifyState -Path $Path
        if ($existing.last_notified_at) {
            $obj.last_notified_at = [string]$existing.last_notified_at
        }
        else {
            $obj.last_notified_at = ''
        }
    }

    ($obj | ConvertTo-Json -Depth 4) | Set-Content -Path $Path -Encoding UTF8
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.unified_api_url) { $unifiedApiUrl = [string]$cfg.unified_api_url }
        if ($cfg.comfyui_url) { $comfyUiUrl = [string]$cfg.comfyui_url }
        if ($cfg.log_file) { $logFile = [string]$cfg.log_file }
        if ($cfg.webhook_url) { $webhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_format) { $webhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_mention) { $webhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.notify_on_success) { $notifyOnSuccess = [bool]$cfg.notify_on_success }
        if ($null -ne $cfg.notify_cooldown_minutes) { $notifyCooldownMinutes = [int]$cfg.notify_cooldown_minutes }
        if ($cfg.notify_state_file) { $notifyStateFile = [string]$cfg.notify_state_file }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_COOLDOWN_MINUTES)) {
    try {
        $notifyCooldownMinutes = [int]$env:MANAOS_NOTIFY_COOLDOWN_MINUTES
    }
    catch {
        Write-Host "[WARN] Invalid MANAOS_NOTIFY_COOLDOWN_MINUTES: $($env:MANAOS_NOTIFY_COOLDOWN_MINUTES)" -ForegroundColor Yellow
    }
}

if ($notifyCooldownMinutes -lt 0) {
    $notifyCooldownMinutes = 0
}

$logDir = Split-Path -Parent $logFile
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$notify = Resolve-NotifySettings -InWebhookUrl $webhookUrl -InWebhookFormat $webhookFormat -InWebhookMention $webhookMention -InNotifyOnSuccess ([bool]$notifyOnSuccess)
$webhookUrl = [string]$notify.webhook_url
$webhookFormat = [string]$notify.webhook_format
$webhookMention = [string]$notify.webhook_mention
$notifyOnSuccess = [bool]$notify.notify_on_success

$probeJson = & $probeScript -ProbeGenerate -Json -UnifiedApiUrl $unifiedApiUrl -ComfyUiUrl $comfyUiUrl
$probeJson | Set-Content -Path $logFile -Encoding UTF8
$probe = $probeJson | ConvertFrom-Json

$unifiedReady = [bool]$probe.unified_api.ready
$directReady = [bool]$probe.comfyui.ready
$overallOk = ($unifiedReady -or $directReady)

$routeCategory = if ($unifiedReady) {
    'unified_ready'
} elseif ($directReady) {
    'direct_fallback'
} else {
    'pipeline_down'
}

$msg = "category=$routeCategory unifiedReady=$unifiedReady directReady=$directReady unifiedApi=$unifiedApiUrl comfyUi=$comfyUiUrl"
$now = [datetimeoffset]::Now
$notifyState = Load-NotifyState -Path $notifyStateFile
$lastStatus = [string]$notifyState.last_status
$lastNotifiedAt = $null
if (-not [string]::IsNullOrWhiteSpace([string]$notifyState.last_notified_at)) {
    try {
        $lastNotifiedAt = [datetimeoffset]::Parse([string]$notifyState.last_notified_at)
    }
    catch {
        $lastNotifiedAt = $null
    }
}

if (-not $overallOk) {
    Write-Host "[ALERT] Image pipeline probe failed | $msg" -ForegroundColor Red
    $shouldNotifyFailure = $false
    if ($lastStatus -ne 'failure') {
        $shouldNotifyFailure = $true
    }
    elseif ($null -eq $lastNotifiedAt) {
        $shouldNotifyFailure = $true
    }
    else {
        $elapsed = ($now - $lastNotifiedAt).TotalMinutes
        if ($elapsed -ge $notifyCooldownMinutes) {
            $shouldNotifyFailure = $true
        }
    }

    if ($shouldNotifyFailure -and -not [string]::IsNullOrWhiteSpace($webhookUrl)) {
        Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'failure' -Title '[Image Pipeline Probe] FAILURE (pipeline_down)' -Body $msg -Mention $webhookMention
        Save-NotifyState -Path $notifyStateFile -Status 'failure' -Category $routeCategory -MarkNotified
    }
    else {
        if (-not [string]::IsNullOrWhiteSpace($webhookUrl)) {
            Write-Host "[INFO] Failure notify skipped by cooldown ($notifyCooldownMinutes min)" -ForegroundColor DarkGray
        }
        Save-NotifyState -Path $notifyStateFile -Status 'failure' -Category $routeCategory
    }
    Write-Host "[INFO] Image pipeline probe saved: $logFile" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Image pipeline probe healthy | $msg" -ForegroundColor Green
if ($notifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($webhookUrl) -and $lastStatus -eq 'failure') {
    Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'success' -Title "[Image Pipeline Probe] SUCCESS ($routeCategory)" -Body $msg -Mention $webhookMention
    Save-NotifyState -Path $notifyStateFile -Status 'success' -Category $routeCategory -MarkNotified
}
else {
    Save-NotifyState -Path $notifyStateFile -Status 'success' -Category $routeCategory
}

Write-Host "[OK] Image pipeline probe saved: $logFile" -ForegroundColor Green
exit 0
