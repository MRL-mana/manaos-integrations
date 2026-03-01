param(
    [string]$TaskName = "ManaOS_Dashboard_Alert",
    [int]$IntervalMinutes = 5,
    [int]$WindowMinutes = 10,
    [int]$FailThreshold = 3
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repo "tools\alert_dashboard_fail.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "alert script not found: $scriptPath"
}

$escapedScript = $scriptPath.Replace('"', '""')
$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedScript`" -WindowMinutes $WindowMinutes -FailThreshold $FailThreshold"

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /TR $tr /F | Out-Null

schtasks /Query /TN $TaskName /FO LIST
