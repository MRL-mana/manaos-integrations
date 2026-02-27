param(
    [string]$TaskName = "ManaOS_Image_Pipeline_Probe_5min",
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\image_pipeline_probe_task.config.json"
}

Write-Host "=== Image Pipeline Probe Task Status ===" -ForegroundColor Cyan
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
    Write-Host "unified_api_url: $($cfg.unified_api_url)" -ForegroundColor Gray
    Write-Host "comfyui_url: $($cfg.comfyui_url)" -ForegroundColor Gray
    Write-Host "history_file: $($cfg.history_file)" -ForegroundColor Gray
    Write-Host "state_file: $($cfg.state_file)" -ForegroundColor Gray
    Write-Host "enable_auto_recovery: $($cfg.enable_auto_recovery)" -ForegroundColor Gray
    Write-Host "enable_auto_recovery_on_unified_degraded: $($cfg.enable_auto_recovery_on_unified_degraded)" -ForegroundColor Gray
    Write-Host "notify_cooldown_minutes: $($cfg.notify_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "notify_unified_degraded_after: $($cfg.notify_unified_degraded_after)" -ForegroundColor Gray
    Write-Host "notify_unified_degraded_cooldown_minutes: $($cfg.notify_unified_degraded_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "notify_state_file: $($cfg.notify_state_file)" -ForegroundColor Gray

    $latestFile = [string]$cfg.log_file
    if (-not [string]::IsNullOrWhiteSpace($latestFile) -and (Test-Path $latestFile)) {
        try {
            $latest = Get-Content -Path $latestFile -Raw | ConvertFrom-Json
            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_ts: $($latest.generated_at)" -ForegroundColor Gray
            Write-Host "latest_route_category: $($latest.route.category)" -ForegroundColor Gray
            Write-Host "latest_overall_ok: $($latest.overall.ok)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse latest output file: $latestFile" -ForegroundColor Yellow
        }
    }

    $historyFile = [string]$cfg.history_file
    if (-not [string]::IsNullOrWhiteSpace($historyFile) -and (Test-Path $historyFile)) {
        try {
            $historyLast = Get-Content -Path $historyFile -Tail 1 | ConvertFrom-Json
            Write-Host "latest_failure_category: $($historyLast.failure_category)" -ForegroundColor Gray
            Write-Host "latest_failure_notified: $($historyLast.failure_notified)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_suppressed_reason: $($historyLast.failure_notify_suppressed_reason)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse history tail: $historyFile" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
}

exit 0
