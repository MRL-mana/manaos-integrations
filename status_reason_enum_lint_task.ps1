param(
    [string]$TaskName = "ManaOS_Reason_Enum_Lint_60min",
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}

Write-Host "=== Reason Enum Lint Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: task_not_found" -ForegroundColor Gray
    Write-Host "latest_exit_code: -1" -ForegroundColor Gray
    exit 1
}

$taskInfo | ForEach-Object { Write-Host $_ }

$taskToRunLine = $taskInfo | Where-Object { $_ -match '^(Task To Run|実行するタスク):\s*' } | Select-Object -First 1
if (-not [string]::IsNullOrWhiteSpace($taskToRunLine)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $taskToRunLine" -ForegroundColor Gray
    if ($taskToRunLine -notmatch '-ConfigFile') {
        Write-Host "[WARN] Task command does not include -ConfigFile. Runtime defaults will be used." -ForegroundColor Yellow
    }
}

Write-Host "ConfigFile: $ConfigFile" -ForegroundColor Gray
if (-not (Test-Path $ConfigFile)) {
    Write-Host "[WARN] Config file not found: $ConfigFile" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
    Write-Host "latest_exit_code: -1" -ForegroundColor Gray
    exit 0
}

try {
    $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
    Write-Host "--- Config Summary ---" -ForegroundColor Cyan
    Write-Host "repo_root: $($cfg.repo_root)" -ForegroundColor Gray
    Write-Host "include_check_scripts: $($cfg.include_check_scripts)" -ForegroundColor Gray
    Write-Host "latest_json_file: $($cfg.latest_json_file)" -ForegroundColor Gray
    Write-Host "history_jsonl: $($cfg.history_jsonl)" -ForegroundColor Gray
    Write-Host "webhook_format: $($cfg.webhook_format)" -ForegroundColor Gray
    Write-Host "webhook_enabled: $(-not [string]::IsNullOrWhiteSpace([string]$cfg.webhook_url))" -ForegroundColor Gray
    Write-Host "notify_failure_cooldown_minutes: $($cfg.notify_failure_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "notify_state_file: $($cfg.notify_state_file)" -ForegroundColor Gray

    $latestJson = [string]$cfg.latest_json_file
    if (-not [string]::IsNullOrWhiteSpace($latestJson) -and (Test-Path $latestJson)) {
        try {
            $latest = Get-Content -Path $latestJson -Raw | ConvertFrom-Json
            $latestTs = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
            $latestOk = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
            $latestOkReason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
            $latestExitCode = if ($null -ne $latest.exit_code) { [int]$latest.exit_code } else { -1 }

            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_ts: $latestTs" -ForegroundColor Gray
            Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
            Write-Host "latest_ok_reason: $latestOkReason" -ForegroundColor Gray
            Write-Host "latest_exit_code: $latestExitCode" -ForegroundColor Gray
            Write-Host "latest_include_check_scripts: $($latest.include_check_scripts)" -ForegroundColor Gray
            Write-Host "latest_failure_category: $($latest.failure_category)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_attempted: $($latest.failure_notify_attempted)" -ForegroundColor Gray
            Write-Host "latest_failure_notified: $($latest.failure_notified)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_suppressed_reason: $($latest.failure_notify_suppressed_reason)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse latest output file: $latestJson" -ForegroundColor Yellow
            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_ts: N/A" -ForegroundColor Gray
            Write-Host "latest_ok: False" -ForegroundColor Gray
            Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
            Write-Host "latest_exit_code: -1" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "--- Latest Output ---" -ForegroundColor Cyan
        Write-Host "latest_ts: N/A" -ForegroundColor Gray
        Write-Host "latest_ok: False" -ForegroundColor Gray
        Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
        Write-Host "latest_exit_code: -1" -ForegroundColor Gray
        if (-not [string]::IsNullOrWhiteSpace($latestJson)) {
            Write-Host "[WARN] Latest output file not found: $latestJson" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
    Write-Host "latest_exit_code: -1" -ForegroundColor Gray
}

exit 0
