param(
    [string]$TaskName = "ManaOS_Reason_Enum_Ops_Snapshot_30min",
    [string]$LatestJsonFile = "",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot.latest.json"
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
    snapshot_found = $false
    snapshot_ts = 'N/A'
    snapshot_ok = $false
    snapshot_ok_reason = 'source_missing'
    lint_latest_ok_reason = 'source_missing'
    cooldown_verify_status_ok_reason = 'source_missing'
    lifecycle_status_ok_reason = 'source_missing'
}

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST 2>$null
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    $payload.snapshot_ok_reason = 'task_not_found'
    if ($AsJson) {
        Write-Output ($payload | ConvertTo-Json -Depth 8)
    }
    else {
        Write-Host "=== Reason Enum Ops Snapshot Task Status ===" -ForegroundColor Cyan
        Write-Host "TaskName: $TaskName" -ForegroundColor Gray
        Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
        Write-Host "snapshot_ok_reason: task_not_found" -ForegroundColor Gray
    }
    exit 1
}

$payload.task_found = $true
$payload.task_to_run = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Task To Run|実行するタスク):\s*'
$payload.task_last_result = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Last Result|前回の結果):\s*'

if (Test-Path $LatestJsonFile) {
    try {
        $latest = Get-Content -Path $LatestJsonFile -Raw | ConvertFrom-Json
        $payload.snapshot_found = $true
        $payload.snapshot_ts = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
        $payload.snapshot_ok = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
        $payload.snapshot_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
        if ($null -ne $latest.lint) {
            $payload.lint_latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.lint.latest_ok_reason)) { [string]$latest.lint.latest_ok_reason } else { 'source_missing' }
        }
        if ($null -ne $latest.cooldown_verify) {
            $payload.cooldown_verify_status_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.cooldown_verify.status_ok_reason)) { [string]$latest.cooldown_verify.status_ok_reason } else { 'source_missing' }
        }
        if ($null -ne $latest.lifecycle) {
            $payload.lifecycle_status_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.lifecycle.status_ok_reason)) { [string]$latest.lifecycle.status_ok_reason } else { 'source_missing' }
        }
    }
    catch {
        $payload.snapshot_ok = $false
        $payload.snapshot_ok_reason = 'source_missing'
    }
}

if ($AsJson) {
    Write-Output ($payload | ConvertTo-Json -Depth 8)
    exit 0
}

Write-Host "=== Reason Enum Ops Snapshot Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
$taskInfo | ForEach-Object { Write-Host $_ }
if (-not [string]::IsNullOrWhiteSpace($payload.task_to_run)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $($payload.task_to_run)" -ForegroundColor Gray
}
Write-Host "latest_json_file: $LatestJsonFile" -ForegroundColor Gray
Write-Host "snapshot_found: $($payload.snapshot_found)" -ForegroundColor Gray
Write-Host "snapshot_ts: $($payload.snapshot_ts)" -ForegroundColor Gray
Write-Host "snapshot_ok: $($payload.snapshot_ok)" -ForegroundColor Gray
Write-Host "snapshot_ok_reason: $($payload.snapshot_ok_reason)" -ForegroundColor Gray
Write-Host "lint_latest_ok_reason: $($payload.lint_latest_ok_reason)" -ForegroundColor Gray
Write-Host "cooldown_verify_status_ok_reason: $($payload.cooldown_verify_status_ok_reason)" -ForegroundColor Gray
Write-Host "lifecycle_status_ok_reason: $($payload.lifecycle_status_ok_reason)" -ForegroundColor Gray

exit 0
