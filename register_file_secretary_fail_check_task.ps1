param(
    [string]$TaskName = "ManaOS_File_Secretary_FailCheck",
    [int]$IntervalMinutes = 5,
    [int]$FailThreshold = 3,
    [int]$TailLines = 200,
    [int]$CooldownMinutes = 30,
    [switch]$SkipResolveWebhook
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repo "tools\run_file_secretary_fail_check.ps1"
$resolverPath = Join-Path $repo "tools\resolve_existing_webhook.ps1"
$logDir = Join-Path $repo "logs"
$launcherPath = Join-Path $logDir "run_file_secretary_fail_check_task.cmd"

if (-not (Test-Path $scriptPath)) {
    throw "run script not found: $scriptPath"
}

if (-not $SkipResolveWebhook -and (Test-Path $resolverPath)) {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $resolverPath -Apply | Out-Null
    }
    catch {
        Write-Host "[WARN] webhook resolver failed during register: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$escapedScript = $scriptPath.Replace('"', '""')

$launcherContent = @(
    "@echo off",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedScript`" -FailThreshold $FailThreshold -TailLines $TailLines -CooldownMinutes $CooldownMinutes"
) -join "`r`n"
Set-Content -Path $launcherPath -Value $launcherContent -Encoding Ascii

$escapedLauncher = $launcherPath.Replace('"', '""')
$tr = "`"$escapedLauncher`""

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /TR $tr /F | Out-Null

schtasks /Query /TN $TaskName /FO LIST
