param(
    [string]$TaskName = "ManaOS_Reason_Enum_Lint_60min",
    [string]$ConfigFile = "",
    [int]$NotifyFailureCooldownMinutes = 60,
    [int]$WaitAfterRunSeconds = 6,
    [switch]$SkipHealthyRestore
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}

if (-not (Test-Path $ConfigFile)) {
    throw "Config file not found: $ConfigFile"
}
if ($NotifyFailureCooldownMinutes -lt 1) {
    throw "NotifyFailureCooldownMinutes must be >= 1"
}
if ($WaitAfterRunSeconds -lt 2) {
    throw "WaitAfterRunSeconds must be >= 2"
}

$taskCheck = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "Scheduled task not found: $TaskName"
}

$runOnceScript = Join-Path $scriptDir "run_reason_enum_lint_once.ps1"
if (-not (Test-Path $runOnceScript)) {
    throw "Runner script not found: $runOnceScript"
}

$cfgBackup = "$ConfigFile.bak.cooldown_verify"
$tmpRepo = Join-Path $scriptDir ".tmp_reason_lint_sched_fail"

$cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
$latestJsonFile = [string]$cfg.latest_json_file
$historyJsonl = [string]$cfg.history_jsonl
$notifyStateFile = [string]$cfg.notify_state_file

if ([string]::IsNullOrWhiteSpace($latestJsonFile)) {
    throw "latest_json_file is empty in config: $ConfigFile"
}
if ([string]::IsNullOrWhiteSpace($notifyStateFile)) {
    throw "notify_state_file is empty in config: $ConfigFile"
}

Copy-Item -Path $ConfigFile -Destination $cfgBackup -Force

try {
    if (Test-Path $tmpRepo) {
        Remove-Item -Path $tmpRepo -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tmpRepo | Out-Null
    Copy-Item -Path (Join-Path $scriptDir "lint_reason_enum.ps1") -Destination (Join-Path $tmpRepo "lint_reason_enum.ps1") -Force

    $cfg.repo_root = $tmpRepo
    $cfg.webhook_url = "http://127.0.0.1:9/webhook"
    $cfg.notify_failure_cooldown_minutes = [int]$NotifyFailureCooldownMinutes
    $cfg.updated_at = [datetimeoffset]::Now.ToString('o')
    ($cfg | ConvertTo-Json -Depth 8) | Set-Content -Path $ConfigFile -Encoding UTF8

    $notifyDir = Split-Path -Parent $notifyStateFile
    if ($notifyDir -and -not (Test-Path $notifyDir)) {
        New-Item -ItemType Directory -Path $notifyDir -Force | Out-Null
    }

    $now = [datetimeoffset]::Now.ToString('o')
    @{
        last_failure_notified_at = $now
        last_status = 'failure'
        updated_at = $now
    } | ConvertTo-Json -Depth 4 | Set-Content -Path $notifyStateFile -Encoding UTF8

    schtasks /Run /TN $TaskName | Out-Null
    Start-Sleep -Seconds $WaitAfterRunSeconds
    schtasks /Run /TN $TaskName | Out-Null
    Start-Sleep -Seconds $WaitAfterRunSeconds

    if (-not (Test-Path $latestJsonFile)) {
        throw "Latest json not found: $latestJsonFile"
    }

    $latest = Get-Content -Path $latestJsonFile -Raw | ConvertFrom-Json
    $suppressed = [string]$latest.failure_notify_suppressed_reason

    Write-Host "=== Cooldown Verify Result ===" -ForegroundColor Cyan
    Write-Host "latest_ok: $($latest.ok)" -ForegroundColor Gray
    Write-Host "latest_ok_reason: $($latest.ok_reason)" -ForegroundColor Gray
    Write-Host "latest_failure_category: $($latest.failure_category)" -ForegroundColor Gray
    Write-Host "latest_failure_notify_attempted: $($latest.failure_notify_attempted)" -ForegroundColor Gray
    Write-Host "latest_failure_notified: $($latest.failure_notified)" -ForegroundColor Gray
    Write-Host "latest_failure_notify_suppressed_reason: $suppressed" -ForegroundColor Gray

    if ($latest.ok -ne $false) {
        throw "Expected latest.ok=False during failure simulation"
    }
    if ([string]::IsNullOrWhiteSpace($suppressed) -or $suppressed -notmatch '^same_category_cooldown\([0-9]+m_remaining\)$') {
        throw "Expected cooldown suppression reason, got: $suppressed"
    }

    Write-Host "[OK] Cooldown suppression verified via scheduled task" -ForegroundColor Green
}
finally {
    if (Test-Path $cfgBackup) {
        Move-Item -Path $cfgBackup -Destination $ConfigFile -Force
    }
    if (Test-Path $tmpRepo) {
        Remove-Item -Path $tmpRepo -Recurse -Force
    }

    if (-not $SkipHealthyRestore.IsPresent) {
        try {
            & pwsh -NoProfile -ExecutionPolicy Bypass -File $runOnceScript -ConfigFile $ConfigFile | Out-Null
        }
        catch {
            Write-Host "[WARN] Healthy restore run failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

exit 0
