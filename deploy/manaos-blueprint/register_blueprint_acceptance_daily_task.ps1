param(
    [string]$TaskName = "ManaOS-Blueprint-Acceptance-Daily",
    [string]$StartTime = "07:30",
    [string]$BaseDomain = "mrl-mana.com",
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pipelineScript = Join-Path $scriptDir "run_blueprint_full_pipeline.ps1"

if (-not (Test-Path $pipelineScript)) {
    throw "pipeline script not found: $pipelineScript"
}

if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_URL", $WebhookUrl, "User")
}

if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", $WebhookMention, "User")
}

if (-not [string]::IsNullOrWhiteSpace($WebhookFormat)) {
    [Environment]::SetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", $WebhookFormat, "User")
}

if ($NotifyOnSuccess) {
    [Environment]::SetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "true", "User")
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$pipelineScript`" -BaseDomain `"$BaseDomain`" -StartIfNeeded"

schtasks /Create /SC DAILY /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
schtasks /Query /TN $TaskName /V /FO LIST
