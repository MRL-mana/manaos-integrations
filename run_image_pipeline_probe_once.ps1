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
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
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

if (-not $overallOk) {
    Write-Host "[ALERT] Image pipeline probe failed | $msg" -ForegroundColor Red
    if (-not [string]::IsNullOrWhiteSpace($webhookUrl)) {
        Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'failure' -Title '[Image Pipeline Probe] FAILURE (pipeline_down)' -Body $msg -Mention $webhookMention
    }
    Write-Host "[INFO] Image pipeline probe saved: $logFile" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Image pipeline probe healthy | $msg" -ForegroundColor Green
if ($notifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($webhookUrl)) {
    Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'success' -Title "[Image Pipeline Probe] SUCCESS ($routeCategory)" -Body $msg -Mention $webhookMention
}

Write-Host "[OK] Image pipeline probe saved: $logFile" -ForegroundColor Green
exit 0
