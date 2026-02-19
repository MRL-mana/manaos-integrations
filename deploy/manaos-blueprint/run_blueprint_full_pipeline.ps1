param(
    [string]$BaseDomain,
    [string]$AdminEmail = "mana-blueprint-admin@example.local",
    [string]$AdminPassword = "ManaOS!2026",
    [switch]$StartIfNeeded,
    [switch]$BootstrapSignup,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
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

function Send-WebhookNotification {
    param(
        [ValidateSet("generic", "slack", "discord")]
        [string]$Format,
        [string]$Url,
        [string]$Mention,
        [string]$Status,
        [string]$Base,
        [string]$Log,
        [string]$Reason
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }

    $prefix = if ([string]::IsNullOrWhiteSpace($Mention)) { "" } else { "$Mention " }
    $reasonLine = if ([string]::IsNullOrWhiteSpace($Reason)) { "" } else { "`nreason: $Reason" }
    $text = "${prefix}Blueprint full pipeline ${Status}`nbase_domain: ${Base}`nlog: ${Log}${reasonLine}".Trim()

    if ($Format -eq "discord") {
        $body = @{ content = $text }
    }
    else {
        $body = @{ text = $text }
    }

    try {
        Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 5 -Compress) -TimeoutSec 20 | Out-Null
        Write-Host "[OK] Webhook notified ($Status)" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Webhook notify failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrapScript = Join-Path $scriptDir "bootstrap_openwebui_tools.py"
$acceptanceScript = Join-Path $scriptDir "run_blueprint_acceptance.ps1"
$composeFile = Join-Path $scriptDir "docker-compose.blueprint.yml"
$envPath = Join-Path $scriptDir ".env"

if (-not (Test-Path $bootstrapScript)) {
    throw "bootstrap script not found: $bootstrapScript"
}
if (-not (Test-Path $acceptanceScript)) {
    throw "acceptance script not found: $acceptanceScript"
}

if (-not $BaseDomain -and (Test-Path $envPath)) {
    $line = Get-Content $envPath | Where-Object { $_ -match '^BASE_DOMAIN=' } | Select-Object -First 1
    if ($line) {
        $BaseDomain = ($line -split '=', 2)[1].Trim()
    }
}

if (-not $BaseDomain) {
    $BaseDomain = "mrl-mana.com"
}

$logDir = Join-Path $scriptDir "..\..\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "blueprint_pipeline_$stamp.log"

Step "Blueprint full pipeline"
Write-Host "BaseDomain: $BaseDomain" -ForegroundColor Gray
Write-Host "Log: $logPath" -ForegroundColor Gray

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

$bootstrapArgs = @(
    $bootstrapScript,
    "--base-domain", $BaseDomain,
    "--email", $AdminEmail,
    "--password", $AdminPassword
)

if ($BootstrapSignup) {
    $bootstrapArgs += "--signup"
}

$pipelineStatus = "FAIL"
$failureReason = ""

try {
    if ($StartIfNeeded) {
        Step "Start blueprint stack"
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        docker compose -f $composeFile --env-file $envPath up -d 2>$null | Tee-Object -FilePath $logPath -Append | Out-Host
        $ErrorActionPreference = $prevEap
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up failed (exit=$LASTEXITCODE)"
        }

        Step "Wait for API health"
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            try {
                Invoke-RestMethod -Method GET -Uri "http://localhost/health" -Headers @{ Host = "api.$BaseDomain" } -TimeoutSec 5 | Out-Null
                $ready = $true
                break
            }
            catch {
            }
            Start-Sleep -Seconds 2
        }

        if (-not $ready) {
            throw "api health is not ready"
        }
    }

    Step "Bootstrap Open WebUI tool"
    python @bootstrapArgs 2>&1 | Tee-Object -FilePath $logPath -Append | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap failed (exit=$LASTEXITCODE)"
    }

    Step "Run blueprint acceptance"
    $acceptanceArgs = @{
        BaseDomain = $BaseDomain
        AdminEmail = $AdminEmail
        AdminPassword = $AdminPassword
    }

    if ($StartIfNeeded) {
        $acceptanceArgs["StartIfNeeded"] = $true
    }

    & $acceptanceScript @acceptanceArgs 2>&1 | Tee-Object -FilePath $logPath -Append | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "acceptance failed (exit=$LASTEXITCODE)"
    }

    $pipelineStatus = "PASS"
}
catch {
    $failureReason = $_.Exception.Message
    Write-Host "[NG] Blueprint full pipeline FAILED: $failureReason" -ForegroundColor Red
}
finally {
    $shouldNotify = (($pipelineStatus -eq "FAIL") -or (($pipelineStatus -eq "PASS") -and $NotifyOnSuccess))
    if ($shouldNotify) {
        Send-WebhookNotification -Format $WebhookFormat -Url $WebhookUrl -Mention $WebhookMention -Status $pipelineStatus -Base $BaseDomain -Log $logPath -Reason $failureReason
    }
}

if ($pipelineStatus -eq "PASS") {
    Step "Pipeline result"
    Write-Host "[OK] Blueprint full pipeline PASSED" -ForegroundColor Green
    Write-Host "Log file: $logPath" -ForegroundColor Green
    exit 0
}

exit 1
