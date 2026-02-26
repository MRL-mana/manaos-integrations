param(
    [string]$BaseUrl = 'http://127.0.0.1:9510',
    [int]$MaxJsonLogSizeMB = 20,
    [int]$MaxJsonLogFiles = 5,
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = 'discord',
    [string]$WebhookUrl = '',
    [string]$WebhookMention = '',
    [switch]$NotifyOnSuccess
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $scriptDir 'run_r12_health_watch.ps1'
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logPath = Join-Path $repoRoot 'logs\r12_health_watch_task.jsonl'

if (-not (Test-Path $mainScript)) {
    throw "Main script not found: $mainScript"
}

$forward = @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $mainScript,
    '-BaseUrl', $BaseUrl,
    '-Once',
    '-FailOnError',
    '-JsonLogPath', $logPath,
    '-MaxJsonLogSizeMB', "$MaxJsonLogSizeMB",
    '-MaxJsonLogFiles', "$MaxJsonLogFiles",
    '-WebhookFormat', $WebhookFormat
)

if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $forward += @('-WebhookUrl', $WebhookUrl)
}
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    $forward += @('-WebhookMention', $WebhookMention)
}
if ($NotifyOnSuccess.IsPresent) {
    $forward += '-NotifyOnSuccess'
}

pwsh @forward
