param(
    [string]$TaskName = "ManaOS_Tailscale_FullStack_KeepAlive_5min"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configFile = Join-Path $scriptDir "logs\tailscale_full_stack_keepalive.task.config.json"
$latestFile = Join-Path $scriptDir "logs\tailscale_full_stack_keepalive.latest.json"

Write-Host "=== Tailscale FullStack KeepAlive Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    exit 1
}

$taskInfo | ForEach-Object { Write-Host $_ }

if (Test-Path $configFile) {
    try {
        $cfg = Get-Content -Path $configFile -Raw | ConvertFrom-Json
        Write-Host "--- Config ---" -ForegroundColor Cyan
        Write-Host "interval_minutes: $($cfg.interval_minutes)" -ForegroundColor Gray
        Write-Host "run_level: $($cfg.run_level)" -ForegroundColor Gray
        Write-Host "run_as_system: $($cfg.run_as_system)" -ForegroundColor Gray
        Write-Host "skip_firewall: $($cfg.skip_firewall)" -ForegroundColor Gray
        Write-Host "updated_at: $($cfg.updated_at)" -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Failed to parse config: $configFile" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[WARN] Config file not found: $configFile" -ForegroundColor Yellow
}

if (Test-Path $latestFile) {
    try {
        $latest = Get-Content -Path $latestFile -Raw | ConvertFrom-Json
        Write-Host "--- Latest Run ---" -ForegroundColor Cyan
        Write-Host "ts: $($latest.ts)" -ForegroundColor Gray
        Write-Host "ok: $($latest.ok)" -ForegroundColor Gray
        Write-Host "error: $($latest.error)" -ForegroundColor Gray
        Write-Host "started_at: $($latest.started_at)" -ForegroundColor Gray
        Write-Host "ended_at: $($latest.ended_at)" -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Failed to parse latest file: $latestFile" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[INFO] Latest run file not found: $latestFile" -ForegroundColor DarkGray
}

exit 0
