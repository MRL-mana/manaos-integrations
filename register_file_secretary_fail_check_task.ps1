param(
    [string]$TaskName = "ManaOS_File_Secretary_FailCheck",
    [int]$IntervalMinutes = 5,
    [int]$FailThreshold = 3,
    [int]$TailLines = 200,
    [int]$CooldownMinutes = 30
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repo "tools\run_file_secretary_fail_check.ps1"
$logDir = Join-Path $repo "logs"
$launcherPath = Join-Path $logDir "run_file_secretary_fail_check_task.cmd"

if (-not (Test-Path $scriptPath)) {
    throw "run script not found: $scriptPath"
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
