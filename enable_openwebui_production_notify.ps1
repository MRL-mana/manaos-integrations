param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [string]$DailyTime = "09:00",
    [int]$MaxAgeMinutes = 180,
    [int]$VerifyDelaySeconds = 180
)

$ErrorActionPreference = "Stop"

function Write-Step($text) {
    Write-Host "`n== $text ==" -ForegroundColor Cyan
}

function Test-WebhookEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [ValidateSet("generic", "slack", "discord")]
        [string]$Format = "discord"
    )

    $payload = @{
        content = "manaos webhook preflight"
        text = "manaos webhook preflight"
        username = "ManaOS"
    } | ConvertTo-Json -Compress

    try {
        Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $payload -TimeoutSec 15 | Out-Null
        return
    }
    catch {
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }

        $detail = ""
        if ($_.ErrorDetails -and $null -ne $_.ErrorDetails.Message) {
            $detail = [string]$_.ErrorDetails.Message
        }

        if ($status -eq 404 -and $detail -match '"code"\s*:\s*10015|Unknown Webhook') {
            throw "Webhook URL is invalid or deleted (Discord code 10015). Update -WebhookUrl and retry."
        }

        if ($status) {
            throw "Webhook preflight failed with HTTP $status. $detail"
        }

        throw "Webhook preflight failed: $($_.Exception.Message)"
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$setEnvScript = Join-Path $scriptRoot "set_openwebui_notify_env.ps1"
$operateScript = Join-Path $scriptRoot "operate_openwebui_production.ps1"
$registerDailyScript = Join-Path $scriptRoot "register_openwebui_daily_health.ps1"
$checkScript = Join-Path $scriptRoot "check_openwebui_production.ps1"

foreach ($required in @($setEnvScript, $operateScript, $registerDailyScript, $checkScript)) {
    if (-not (Test-Path $required)) {
        throw "Missing script: $required"
    }
}

Write-Host "Enable OpenWebUI production notification" -ForegroundColor Green

Write-Step "Persist notification environment"
$envParams = @{
    WebhookUrl = $WebhookUrl
    WebhookFormat = $WebhookFormat
    WebhookMention = $WebhookMention
}
if ($NotifyOnSuccess) {
    $envParams.NotifyOnSuccess = $true
}
& $setEnvScript @envParams -ErrorAction Continue
# Note: set env script may have non-zero exit code but still succeed, check env var presence
if (-not (Test-Path Env:MANAOS_WEBHOOK_URL)) {
    throw "Failed to save notification environment"
}

Write-Step "Webhook preflight"
Test-WebhookEndpoint -Url $WebhookUrl -Format $WebhookFormat
Write-Host "[OK] Webhook endpoint is reachable" -ForegroundColor Green

Write-Step "Run production operation"
& $operateScript -VerifyDelaySeconds $VerifyDelaySeconds
if ($LASTEXITCODE -ne 0) {
    throw "Production operation failed"
}

Write-Step "Re-register daily health"
& $registerDailyScript -DailyTime $DailyTime -MaxAgeMinutes $MaxAgeMinutes -RequireStartupSource -AutoRecoverOnFailure -VerifyDelaySeconds $VerifyDelaySeconds
if ($LASTEXITCODE -ne 0) {
    throw "Daily health registration failed"
}

Write-Step "Final health check"
& $checkScript -RequireStartupSource -MaxAgeMinutes $MaxAgeMinutes -AutoRecoverOnFailure -VerifyDelaySeconds $VerifyDelaySeconds
if ($LASTEXITCODE -ne 0) {
    throw "Final production health check failed"
}

Write-Host "" 
Write-Host "[OK] Notification-enabled production operation is active" -ForegroundColor Green
