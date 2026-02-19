param(
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [int]$VerifyDelaySeconds = 180,
    [int]$MaxAgeMinutes = 30,
    [switch]$RequireStartupSource
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

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $envFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRaw -in @("1", "true", "yes", "on"))
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

$operateScript = Join-Path $scriptRoot "operate_openwebui_production.ps1"
$checkScript = Join-Path $scriptRoot "check_openwebui_production.ps1"
$recoveryStatePath = Join-Path $logsDir "production_recovery_latest.json"
$recoveryHistoryPath = Join-Path $logsDir "production_recovery_history.jsonl"

if (-not (Test-Path $operateScript)) { throw "Missing script: $operateScript" }
if (-not (Test-Path $checkScript)) { throw "Missing script: $checkScript" }

Write-Host "Run production recovery" -ForegroundColor Yellow

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

Write-Step "Re-run Production Operation"
$opParams = @{
    WebhookFormat = $WebhookFormat
    VerifyDelaySeconds = $VerifyDelaySeconds
}
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) { $opParams.WebhookUrl = $WebhookUrl }
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) { $opParams.WebhookMention = $WebhookMention }
if ($NotifyOnSuccess) { $opParams.NotifyOnSuccess = $true }

& $operateScript @opParams
if ($LASTEXITCODE -ne 0) {
    throw "Production operation rerun failed"
}

Write-Step "Post-Recovery Health Check"
$checkParams = @{
    MaxAgeMinutes = $MaxAgeMinutes
}
if ($RequireStartupSource) { $checkParams.RequireStartupSource = $true }

& $checkScript @checkParams
$checkExit = $LASTEXITCODE

$obj = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    recovered = ($checkExit -eq 0)
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    notify_on_success = [bool]$NotifyOnSuccess
    verify_delay_seconds = $VerifyDelaySeconds
    check_max_age_minutes = $MaxAgeMinutes
    require_startup_source = [bool]$RequireStartupSource
}

$obj | ConvertTo-Json -Depth 8 | Set-Content -Path $recoveryStatePath -Encoding UTF8
($obj | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $recoveryHistoryPath -Encoding UTF8

Write-Host "" 
if ($checkExit -eq 0) {
    Write-Host "[OK] Recovery completed" -ForegroundColor Green
    Write-Host ("[OK] Latest state: " + $recoveryStatePath) -ForegroundColor Green
    exit 0
}
else {
    Write-Host "[ERR] Recovery failed" -ForegroundColor Red
    Write-Host ("[ERR] Latest state: " + $recoveryStatePath) -ForegroundColor Red
    exit $checkExit
}
