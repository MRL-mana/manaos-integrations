param(
    [string]$BaseUrl = 'http://127.0.0.1:9510'
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $scriptDir 'run_r12_health_watch.ps1'
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logPath = Join-Path $repoRoot 'logs\r12_health_watch_task.jsonl'

if (-not (Test-Path $mainScript)) {
    throw "Main script not found: $mainScript"
}

pwsh -NoProfile -ExecutionPolicy Bypass -File $mainScript -BaseUrl $BaseUrl -Once -FailOnError -JsonLogPath $logPath
