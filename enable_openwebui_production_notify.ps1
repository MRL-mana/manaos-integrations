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
