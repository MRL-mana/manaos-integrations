param(
    [string]$TaskName = "ManaOS_R12_RL_Ops_Watch_15min",
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\r12_rl_ops_watch_task.config.json"
}

Write-Host "=== R12+RL Ops Watch Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
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
    exit 0
}

try {
    $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
    Write-Host "--- Config Summary ---" -ForegroundColor Cyan
    Write-Host "status_script: $($cfg.status_script)" -ForegroundColor Gray
    Write-Host "json_out_file: $($cfg.json_out_file)" -ForegroundColor Gray
    Write-Host "summary_log_path: $($cfg.summary_log_path)" -ForegroundColor Gray
    Write-Host "notify_on_degraded: $($cfg.notify_on_degraded)" -ForegroundColor Gray
    Write-Host "notify_degraded_after: $($cfg.notify_degraded_after)" -ForegroundColor Gray
    Write-Host "notify_degraded_cooldown_minutes: $($cfg.notify_degraded_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "notify_failure_cooldown_minutes: $($cfg.notify_failure_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "degraded_state_file: $($cfg.degraded_state_file)" -ForegroundColor Gray
    Write-Host "enable_auto_recovery: $($cfg.enable_auto_recovery)" -ForegroundColor Gray
    Write-Host "recover_after_consecutive_endpoint_down: $($cfg.recover_after_consecutive_endpoint_down)" -ForegroundColor Gray
    Write-Host "recovery_cooldown_minutes: $($cfg.recovery_cooldown_minutes)" -ForegroundColor Gray

    $stateFile = [string]$cfg.degraded_state_file
    if (-not [string]::IsNullOrWhiteSpace($stateFile) -and (Test-Path $stateFile)) {
        try {
            $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
            Write-Host "--- Notify State ---" -ForegroundColor Cyan
            Write-Host "state_last_failure_category: $($state.last_failure_category)" -ForegroundColor Gray
            Write-Host "state_last_failure_notified_at: $($state.last_failure_notified_at)" -ForegroundColor Gray
            Write-Host "state_last_degraded_category: $($state.last_degraded_category)" -ForegroundColor Gray
            Write-Host "state_last_degraded_notified_at: $($state.last_degraded_notified_at)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse degraded state file: $stateFile" -ForegroundColor Yellow
        }
    }

    $summaryLogPath = [string]$cfg.summary_log_path
    if (-not [string]::IsNullOrWhiteSpace($summaryLogPath) -and (Test-Path $summaryLogPath)) {
        try {
            $latestSummary = Get-Content -Path $summaryLogPath -Tail 1 | ConvertFrom-Json

            $latestOk = $null
            if ($null -ne $latestSummary.ok) {
                try { $latestOk = [bool]$latestSummary.ok } catch { $latestOk = $null }
            }
            elseif ($null -ne $latestSummary.issues) {
                try {
                    $latestOk = (@($latestSummary.issues).Count -eq 0)
                }
                catch { $latestOk = $null }
            }
            elseif ($null -ne $latestSummary.r12_latest_failed) {
                try {
                    $latestOk = ([int]$latestSummary.r12_latest_failed -eq 0)
                }
                catch { $latestOk = $null }
            }
            elseif (-not [string]::IsNullOrWhiteSpace([string]$latestSummary.failure_category)) {
                $latestOk = $false
            }

            $latestTsDisplay = [string]$latestSummary.ts
            if ([string]::IsNullOrWhiteSpace($latestTsDisplay)) {
                $latestTsDisplay = 'N/A'
            }

            Write-Host "--- Latest Summary ---" -ForegroundColor Cyan
            Write-Host "latest_ts: $latestTsDisplay" -ForegroundColor Gray
            Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
            Write-Host "latest_failure_category: $($latestSummary.failure_category)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_attempted: $($latestSummary.failure_notify_attempted)" -ForegroundColor Gray
            Write-Host "latest_failure_notified: $($latestSummary.failure_notified)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_suppressed_reason: $($latestSummary.failure_notify_suppressed_reason)" -ForegroundColor Gray
            Write-Host "latest_degraded_notify_attempted: $($latestSummary.degraded_notify_attempted)" -ForegroundColor Gray
            Write-Host "latest_degraded_notified: $($latestSummary.degraded_notified)" -ForegroundColor Gray
            Write-Host "latest_degraded_notify_suppressed_reason: $($latestSummary.degraded_notify_suppressed_reason)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse summary log tail: $summaryLogPath" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
}

exit 0
