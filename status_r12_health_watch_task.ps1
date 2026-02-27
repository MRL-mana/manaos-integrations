param(
    [string]$ConfigFile = "",
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min",
    [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\r12_health_watch_task.config.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.task_name) { $TaskName = [string]$cfg.task_name }
        if ($cfg.log_path) { $LogPath = [string]$cfg.log_path }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"
}

function Write-LatestOutput {
    param(
        [string]$Ts,
        [object]$Total,
        [object]$Passed,
        [object]$Failed,
        [object]$Ok,
        [string]$OkReason
    )

    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: $Ts" -ForegroundColor Gray
    Write-Host "latest_total: $Total" -ForegroundColor Gray
    Write-Host "latest_passed: $Passed" -ForegroundColor Gray
    Write-Host "latest_failed: $Failed" -ForegroundColor Gray
    Write-Host "latest_ok: $Ok" -ForegroundColor Gray
    Write-Host "latest_ok_reason: $OkReason" -ForegroundColor Gray
}

Write-Host "=== R12 Health Watch Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_total: N/A" -ForegroundColor Gray
    Write-Host "latest_passed: N/A" -ForegroundColor Gray
    Write-Host "latest_failed: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: task_not_found" -ForegroundColor Gray
    exit 1
}

$taskInfo | ForEach-Object { Write-Host $_ }

$taskToRunLine = $taskInfo | Where-Object { $_ -match '^(Task To Run|実行するタスク):\s*' } | Select-Object -First 1
if (-not [string]::IsNullOrWhiteSpace($taskToRunLine)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $taskToRunLine" -ForegroundColor Gray
}

Write-Host "LogPath: $LogPath" -ForegroundColor Gray
if (Test-Path $LogPath) {
    try {
        $latest = Get-Content -Path $LogPath -Tail 1 | ConvertFrom-Json
        $latestFailed = $null
        try { $latestFailed = [int]$latest.failed } catch { $latestFailed = $null }
        $latestOk = $null
        $latestOkReason = 'ok_missing'
        if ($null -ne $latestFailed) {
            $latestOk = ($latestFailed -eq 0)
            $latestOkReason = 'from_failed_count'
        }

        $latestTsDisplay = [string]$latest.ts
        if ([string]::IsNullOrWhiteSpace($latestTsDisplay)) {
            $latestTsDisplay = 'N/A'
        }

        Write-LatestOutput -Ts $latestTsDisplay -Total $latest.total -Passed $latest.passed -Failed $latest.failed -Ok $latestOk -OkReason $latestOkReason
    }
    catch {
        Write-Host "[WARN] Failed to parse latest log entry: $LogPath" -ForegroundColor Yellow
        Write-LatestOutput -Ts 'N/A' -Total 'N/A' -Passed 'N/A' -Failed 'N/A' -Ok $false -OkReason 'source_missing'
    }
}
else {
    Write-Host "[WARN] Log file not found: $LogPath" -ForegroundColor Yellow
    Write-LatestOutput -Ts 'N/A' -Total 'N/A' -Passed 'N/A' -Failed 'N/A' -Ok $false -OkReason 'source_missing'
}

exit 0
