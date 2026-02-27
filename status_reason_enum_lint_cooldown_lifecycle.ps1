param(
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = "",
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_cooldown_lifecycle.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\reason_enum_cooldown_lifecycle.history.jsonl"
}

$payload = [ordered]@{
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    latest_found = $false
    latest_ts = 'N/A'
    latest_ok = $false
    latest_ok_reason = 'source_missing'
    failed_step_count = -1
    failed_steps = @()
    status_after_summary = @()
    history_found = $false
    history_entries = 0
}

if (Test-Path $LatestJsonFile) {
    try {
        $latest = Get-Content -Path $LatestJsonFile -Raw | ConvertFrom-Json
        $payload.latest_found = $true
        $payload.latest_ts = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
        $payload.latest_ok = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
        $payload.latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
        $payload.failed_step_count = if ($null -ne $latest.failed_step_count) { [int]$latest.failed_step_count } else { -1 }
        $payload.failed_steps = if ($null -ne $latest.failed_steps) { @($latest.failed_steps) } else { @() }
        $payload.status_after_summary = if ($null -ne $latest.status_after_summary) { @($latest.status_after_summary) } else { @() }
    }
    catch {
        $payload.latest_found = $false
        $payload.latest_ok = $false
        $payload.latest_ok_reason = 'source_missing'
    }
}

if (Test-Path $HistoryJsonl) {
    $payload.history_found = $true
    try {
        $payload.history_entries = @(Get-Content -Path $HistoryJsonl).Count
    }
    catch {
        $payload.history_entries = 0
    }
}

if ($AsJson) {
    Write-Output ($payload | ConvertTo-Json -Depth 8)
    exit 0
}

Write-Host "=== Reason Enum Cooldown Lifecycle Status ===" -ForegroundColor Cyan
Write-Host "latest_json_file: $LatestJsonFile" -ForegroundColor Gray
Write-Host "history_jsonl: $HistoryJsonl" -ForegroundColor Gray
Write-Host "latest_found: $($payload.latest_found)" -ForegroundColor Gray
Write-Host "latest_ts: $($payload.latest_ts)" -ForegroundColor Gray
Write-Host "latest_ok: $($payload.latest_ok)" -ForegroundColor Gray
Write-Host "latest_ok_reason: $($payload.latest_ok_reason)" -ForegroundColor Gray
Write-Host "failed_step_count: $($payload.failed_step_count)" -ForegroundColor Gray
Write-Host "failed_steps: $(([string[]]$payload.failed_steps) -join ',')" -ForegroundColor Gray
Write-Host "history_found: $($payload.history_found)" -ForegroundColor Gray
Write-Host "history_entries: $($payload.history_entries)" -ForegroundColor Gray

if (@($payload.status_after_summary).Count -gt 0) {
    Write-Host "--- status_after_summary ---" -ForegroundColor Cyan
    @($payload.status_after_summary) | ForEach-Object { Write-Host ([string]$_) }
}

exit 0
