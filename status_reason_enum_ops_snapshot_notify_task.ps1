param(
    [string]$TaskName = "ManaOS_Reason_Enum_Ops_Snapshot_Notify_30min",
    [string]$LatestJsonFile = "",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot_notify.latest.json"
}

function Get-SchtasksListValue {
    param(
        [string[]]$Lines,
        [string]$Pattern
    )

    $line = $Lines | Where-Object { $_ -match $Pattern } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($line)) {
        return ""
    }
    $parts = $line -split ':', 2
    if ($parts.Count -lt 2) {
        return ""
    }
    return [string]$parts[1].Trim()
}

$payload = [ordered]@{
    task_name = $TaskName
    latest_json_file = $LatestJsonFile
    task_found = $false
    task_to_run = ""
    task_last_result = ""
    latest_found = $false
    latest_ts = 'N/A'
    latest_ok = $false
    latest_ok_reason = 'source_missing'
    latest_failure_notify_suppressed_reason = 'source_missing'
}

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST 2>$null
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    $payload.latest_ok_reason = 'task_not_found'
    if ($AsJson) {
        Write-Output ($payload | ConvertTo-Json -Depth 8)
    }
    else {
        Write-Host "=== Reason Enum Ops Snapshot Notify Task Status ===" -ForegroundColor Cyan
        Write-Host "TaskName: $TaskName" -ForegroundColor Gray
        Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
        Write-Host "latest_ok_reason: task_not_found" -ForegroundColor Gray
    }
    exit 1
}

$payload.task_found = $true
$payload.task_to_run = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Task To Run|実行するタスク):\s*'
$payload.task_last_result = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Last Result|前回の結果):\s*'

if (Test-Path $LatestJsonFile) {
    try {
        $latest = Get-Content -Path $LatestJsonFile -Raw | ConvertFrom-Json
        $payload.latest_found = $true
        $payload.latest_ts = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
        $payload.latest_ok = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
        $payload.latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
        $payload.latest_failure_notify_suppressed_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.failure_notify_suppressed_reason)) { [string]$latest.failure_notify_suppressed_reason } else { '' }
    }
    catch {
        $payload.latest_ok = $false
        $payload.latest_ok_reason = 'source_missing'
        $payload.latest_failure_notify_suppressed_reason = 'source_missing'
    }
}

if ($AsJson) {
    Write-Output ($payload | ConvertTo-Json -Depth 8)
    exit 0
}

Write-Host "=== Reason Enum Ops Snapshot Notify Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
$taskInfo | ForEach-Object { Write-Host $_ }
if (-not [string]::IsNullOrWhiteSpace($payload.task_to_run)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $($payload.task_to_run)" -ForegroundColor Gray
}
Write-Host "latest_json_file: $LatestJsonFile" -ForegroundColor Gray
Write-Host "latest_found: $($payload.latest_found)" -ForegroundColor Gray
Write-Host "latest_ts: $($payload.latest_ts)" -ForegroundColor Gray
Write-Host "latest_ok: $($payload.latest_ok)" -ForegroundColor Gray
Write-Host "latest_ok_reason: $($payload.latest_ok_reason)" -ForegroundColor Gray
Write-Host "latest_failure_notify_suppressed_reason: $($payload.latest_failure_notify_suppressed_reason)" -ForegroundColor Gray

exit 0
