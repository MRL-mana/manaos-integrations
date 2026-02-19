param(
    [string]$WebhookUrl = "",
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [switch]$Clear
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }

if ($Clear) {
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_URL", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", $null, "User")

    Remove-Item Env:MANAOS_WEBHOOK_URL -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_WEBHOOK_FORMAT -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_WEBHOOK_MENTION -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_NOTIFY_ON_SUCCESS -ErrorAction SilentlyContinue

    Write-Ok "Notification environment variables cleared (User + current session)"
    exit 0
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    throw "WebhookUrl is required unless -Clear is specified."
}

$notify = if ($NotifyOnSuccess) { "true" } else { "false" }

[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_URL", $WebhookUrl, "User")
[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", $WebhookFormat, "User")
[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", $WebhookMention, "User")
[Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", $notify, "User")

$env:MANAOS_WEBHOOK_URL = $WebhookUrl
$env:MANAOS_WEBHOOK_FORMAT = $WebhookFormat
$env:MANAOS_WEBHOOK_MENTION = $WebhookMention
$env:MANAOS_NOTIFY_ON_SUCCESS = $notify

Write-Ok "Notification environment variables saved (User + current session)"
Write-Host ("MANAOS_WEBHOOK_FORMAT=" + $WebhookFormat)
Write-Host ("MANAOS_NOTIFY_ON_SUCCESS=" + $notify)
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    Write-Host ("MANAOS_WEBHOOK_MENTION=" + $WebhookMention)
}