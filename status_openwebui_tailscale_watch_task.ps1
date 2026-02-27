param(
    [string]$TaskName = "ManaOS_OpenWebUI_Tailscale_Watch_5min",
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\openwebui_tailscale_watch_task.config.json"
}

Write-Host "=== OpenWebUI Tailscale Watch Task Status ===" -ForegroundColor Cyan
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
    Write-Host "task_name: $($cfg.task_name)" -ForegroundColor Gray
    Write-Host "base_url: $($cfg.base_url)" -ForegroundColor Gray
    Write-Host "log_path: $($cfg.log_path)" -ForegroundColor Gray
    Write-Host "json_out_file: $($cfg.json_out_file)" -ForegroundColor Gray
    Write-Host "webhook_format: $($cfg.webhook_format)" -ForegroundColor Gray
    Write-Host "webhook_enabled: $(-not [string]::IsNullOrWhiteSpace([string]$cfg.webhook_url))" -ForegroundColor Gray
    Write-Host "notify_failure_cooldown_minutes: $($cfg.notify_failure_cooldown_minutes)" -ForegroundColor Gray
    Write-Host "notify_state_file: $($cfg.notify_state_file)" -ForegroundColor Gray

    $latestFile = [string]$cfg.json_out_file
    if (-not [string]::IsNullOrWhiteSpace($latestFile) -and (Test-Path $latestFile)) {
        try {
            $latest = Get-Content -Path $latestFile -Raw | ConvertFrom-Json
            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_ts: $($latest.ts)" -ForegroundColor Gray
            Write-Host "latest_ok: $($latest.ok)" -ForegroundColor Gray
            Write-Host "failure_notified: $($latest.failure_notified)" -ForegroundColor Gray
            Write-Host "failure_notify_suppressed_reason: $($latest.failure_notify_suppressed_reason)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse latest output file: $latestFile" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
}

exit 0
