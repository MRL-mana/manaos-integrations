param(
    [string]$TaskName = "ManaOS_File_Secretary_Run",
    [int]$IntervalMinutes = 5,
    [string]$InboxPath = "00_INBOX",
    [string]$RulesPath = "config/file_secretary_rules.yaml",
    [string]$AuditLogPath = "logs/file_secretary_audit.jsonl"
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repo "tools\run_file_secretary.ps1"
$logDir = Join-Path $repo "logs"
$launcherPath = Join-Path $logDir "run_file_secretary_task.cmd"

if (-not (Test-Path $scriptPath)) {
    throw "run script not found: $scriptPath"
}

$escapedScript = $scriptPath.Replace('"', '""')
$escapedInbox = $InboxPath.Replace('"', '""')
$escapedRules = $RulesPath.Replace('"', '""')
$escapedAudit = $AuditLogPath.Replace('"', '""')

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$launcherContent = @(
    "@echo off",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedScript`" -Inbox `"$escapedInbox`" -Rules `"$escapedRules`" -AuditLog `"$escapedAudit`""
) -join "`r`n"
Set-Content -Path $launcherPath -Value $launcherContent -Encoding Ascii

$escapedLauncher = $launcherPath.Replace('"', '""')
$tr = "`"$escapedLauncher`""

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /TR $tr /F | Out-Null

schtasks /Query /TN $TaskName /FO LIST
