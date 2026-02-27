param(
    [string]$TaskName = "ManaOS_R12_Health_Watch_5min",
    [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"
}

Write-Host "=== R12 Health Watch Task Status ===" -ForegroundColor Cyan
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
}

Write-Host "LogPath: $LogPath" -ForegroundColor Gray
if (Test-Path $LogPath) {
    try {
        $latest = Get-Content -Path $LogPath -Tail 1 | ConvertFrom-Json
        $latestFailed = $null
        try { $latestFailed = [int]$latest.failed } catch { $latestFailed = $null }
        $latestOk = $null
        if ($null -ne $latestFailed) {
            $latestOk = ($latestFailed -eq 0)
        }

        Write-Host "--- Latest Output ---" -ForegroundColor Cyan
        Write-Host "latest_ts: $($latest.ts)" -ForegroundColor Gray
        Write-Host "latest_total: $($latest.total)" -ForegroundColor Gray
        Write-Host "latest_passed: $($latest.passed)" -ForegroundColor Gray
        Write-Host "latest_failed: $($latest.failed)" -ForegroundColor Gray
        Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Failed to parse latest log entry: $LogPath" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[WARN] Log file not found: $LogPath" -ForegroundColor Yellow
}

exit 0
