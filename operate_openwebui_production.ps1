param(
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [int]$VerifyDelaySeconds = 180
)

$ErrorActionPreference = "Stop"

function Write-Step($text) {
    Write-Host "`n== $text ==" -ForegroundColor Cyan
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
    if ([string]::IsNullOrWhiteSpace($resolvedMention)) {
        $resolvedMention = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", "User")
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRaw -in @("1", "true", "yes", "on"))
    }
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User"))) {
        $notifyRawUser = [Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User").Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRawUser -in @("1", "true", "yes", "on"))
    }

    return [ordered]@{
        webhook_url = $resolvedUrl
        webhook_format = $resolvedFormat
        webhook_mention = $resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$finalizeScript = Join-Path $scriptRoot "finalize_openwebui_autostart.ps1"
$statusPath = Join-Path $logsDir "openwebui_tailscale_status.json"
$verifyLogPath = Join-Path $logsDir "verify_openwebui_autostart_last.log"
$opsStatePath = Join-Path $logsDir "production_operation_latest.json"
$opsHistoryPath = Join-Path $logsDir "production_operation_history.jsonl"

if (-not (Test-Path $finalizeScript)) {
    throw "Missing script: $finalizeScript"
}

Write-Host "Start production operation" -ForegroundColor Green

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

$finalizeParams = @{
    WebhookFormat = $WebhookFormat
    VerifyDelaySeconds = $VerifyDelaySeconds
}
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $finalizeParams.WebhookUrl = $WebhookUrl
}
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    $finalizeParams.WebhookMention = $WebhookMention
}
if ($NotifyOnSuccess) {
    $finalizeParams.NotifyOnSuccess = $true
}

Write-Step "Finalize Workflow"
& $finalizeScript @finalizeParams
if ($LASTEXITCODE -ne 0) {
    throw "Finalize workflow failed"
}

$statusObj = $null
if (Test-Path $statusPath) {
    $statusObj = Get-Content -Path $statusPath -Raw | ConvertFrom-Json
}

$verifyTail = ""
if (Test-Path $verifyLogPath) {
    $verifyTail = (Get-Content -Path $verifyLogPath -Tail 40) -join "`n"
}

$operationObj = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    result = "ok"
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    notify_on_success = [bool]$NotifyOnSuccess
    verify_delay_seconds = $VerifyDelaySeconds
    status_file = $statusPath
    verify_log = $verifyLogPath
    local_url = if ($statusObj) { $statusObj.local_url } else { $null }
    tailscale_ip_url = if ($statusObj) { $statusObj.tailscale_ip_url } else { $null }
    tailscale_https_url = if ($statusObj) { $statusObj.tailscale_https_url } else { $null }
    startup_registration = if ($statusObj) { $statusObj.startup_registration } else { $null }
    invocation_source = if ($statusObj) { $statusObj.invocation_source } else { $null }
}

$operationObj | ConvertTo-Json -Depth 8 | Set-Content -Path $opsStatePath -Encoding UTF8
($operationObj | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $opsHistoryPath -Encoding UTF8

Write-Step "Production Summary"
if ($statusObj) {
    Write-Host ("Local URL        : " + $statusObj.local_url) -ForegroundColor White
    Write-Host ("Tailscale IP URL : " + $statusObj.tailscale_ip_url) -ForegroundColor White
    if ($statusObj.tailscale_https_url) {
        Write-Host ("Tailscale HTTPS  : " + $statusObj.tailscale_https_url) -ForegroundColor White
    }
    Write-Host ("Startup mode     : " + $statusObj.startup_registration) -ForegroundColor White
    Write-Host ("Invocation source: " + $statusObj.invocation_source) -ForegroundColor White
}
Write-Host "" 
Write-Host "[OK] Production operation completed" -ForegroundColor Green
Write-Host ("[OK] Latest state: " + $opsStatePath) -ForegroundColor Green
