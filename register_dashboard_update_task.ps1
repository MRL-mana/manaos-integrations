param(
    [string]$TaskName = "ManaOS_Dashboard_Update",
    [int]$IntervalMinutes = 1
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repo "tools\update_dashboard_json.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "update script not found: $scriptPath"
}

$escapedScript = $scriptPath.Replace('"', '""')
$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedScript`""

schtasks /Create /
    TN $TaskName /
    SC MINUTE /
    MO $IntervalMinutes /
    TR $tr /
    F | Out-Null

schtasks /Query /TN $TaskName /FO LIST
