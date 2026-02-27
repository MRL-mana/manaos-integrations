param(
    [string]$ConfigFile = '',
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

function To-Bool {
    param(
        [object]$Value,
        [bool]$Default = $false
    )

    if ($null -eq $Value) { return $Default }
    if ($Value -is [bool]) { return [bool]$Value }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    if ($text -in @('1','true','yes','on','enabled')) { return $true }
    if ($text -in @('0','false','no','off','disabled')) { return $false }
    return $Default
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $scriptDir 'run_r12_health_watch.ps1'
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $repoRoot 'logs\r12_health_watch_task.config.json'
}

$logPath = Join-Path $repoRoot 'logs\r12_health_watch_task.jsonl'

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json

        if (-not $PSBoundParameters.ContainsKey('BaseUrl') -and -not [string]::IsNullOrWhiteSpace([string]$cfg.base_url)) {
            $BaseUrl = [string]$cfg.base_url
        }
        if (-not $PSBoundParameters.ContainsKey('MaxJsonLogSizeMB') -and $null -ne $cfg.max_json_log_size_mb) {
            $MaxJsonLogSizeMB = [int]$cfg.max_json_log_size_mb
        }
        if (-not $PSBoundParameters.ContainsKey('MaxJsonLogFiles') -and $null -ne $cfg.max_json_log_files) {
            $MaxJsonLogFiles = [int]$cfg.max_json_log_files
        }
        if (-not $PSBoundParameters.ContainsKey('WebhookFormat') -and -not [string]::IsNullOrWhiteSpace([string]$cfg.webhook_format)) {
            $WebhookFormat = [string]$cfg.webhook_format
        }
        if (-not $PSBoundParameters.ContainsKey('WebhookUrl') -and -not [string]::IsNullOrWhiteSpace([string]$cfg.webhook_url)) {
            $WebhookUrl = [string]$cfg.webhook_url
        }
        if (-not $PSBoundParameters.ContainsKey('WebhookMention') -and -not [string]::IsNullOrWhiteSpace([string]$cfg.webhook_mention)) {
            $WebhookMention = [string]$cfg.webhook_mention
        }
        if (-not $PSBoundParameters.ContainsKey('NotifyOnSuccess') -and $null -ne $cfg.notify_on_success) {
            $NotifyOnSuccess = To-Bool -Value $cfg.notify_on_success
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$cfg.log_path)) {
            $logPath = [string]$cfg.log_path
        }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

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
