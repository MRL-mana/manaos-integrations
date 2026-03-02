param(
    [string]$WebhookUrl = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [switch]$Clear
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

if ($Clear) {
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_URL", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", $null, "User")
    [Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", $null, "User")

    Remove-Item Env:MANAOS_WEBHOOK_URL -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_WEBHOOK_FORMAT -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_WEBHOOK_MENTION -ErrorAction SilentlyContinue
    Remove-Item Env:MANAOS_NOTIFY_ON_SUCCESS -ErrorAction SilentlyContinue

    Write-Ok "Daily health notify env cleared (User + current session)."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    throw "WebhookUrl is required unless -Clear is specified."
}

$notifyValue = if ($NotifyOnSuccess) { "true" } else { "false" }

[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_URL", $WebhookUrl, "User")
[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", $WebhookFormat, "User")
[Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", $WebhookMention, "User")
[Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", $notifyValue, "User")

$env:MANAOS_WEBHOOK_URL = $WebhookUrl
$env:MANAOS_WEBHOOK_FORMAT = $WebhookFormat
$env:MANAOS_WEBHOOK_MENTION = $WebhookMention
$env:MANAOS_NOTIFY_ON_SUCCESS = $notifyValue

Write-Ok "Daily health notify env set (User + current session)."
Write-Host ("MANAOS_WEBHOOK_URL=" + $WebhookUrl)
Write-Host ("MANAOS_WEBHOOK_FORMAT=" + $WebhookFormat)
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    Write-Host ("MANAOS_WEBHOOK_MENTION=" + $WebhookMention)
}
else {
    Write-Warn "MANAOS_WEBHOOK_MENTION is empty"
}
Write-Host ("MANAOS_NOTIFY_ON_SUCCESS=" + $notifyValue)