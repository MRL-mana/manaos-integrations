param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [string]$TaskName = "ManaOS-Blueprint-Acceptance-Daily",
    [string]$StartTime = "07:30",
    [string]$BaseDomain = "mrl-mana.com"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$registerScript = Join-Path $scriptDir "register_blueprint_acceptance_daily_task.ps1"

if (-not (Test-Path $registerScript)) {
    throw "register script not found: $registerScript"
}

[Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "false", "User")
$env:MANAOS_NOTIFY_ON_SUCCESS = "false"

$registerParams = @{
    TaskName = $TaskName
    StartTime = $StartTime
    BaseDomain = $BaseDomain
    WebhookUrl = $WebhookUrl
    WebhookFormat = $WebhookFormat
}

if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    $registerParams["WebhookMention"] = $WebhookMention
}

& $registerScript @registerParams
if ($LASTEXITCODE -ne 0) {
    throw "daily task registration failed (exit=$LASTEXITCODE)"
}

Write-Host "[OK] Blueprint notification preset enabled (failure-only)" -ForegroundColor Green
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
Write-Host "StartTime: $StartTime" -ForegroundColor Gray
Write-Host "NotifyOnSuccess: false" -ForegroundColor Gray
