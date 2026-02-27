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

    $stateFile = [string]$cfg.notify_state_file
    if (-not [string]::IsNullOrWhiteSpace($stateFile) -and (Test-Path $stateFile)) {
        try {
            $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
            Write-Host "--- Notify State ---" -ForegroundColor Cyan
            Write-Host "state_last_failure_category: $($state.last_category)" -ForegroundColor Gray
            Write-Host "state_last_failure_notified_at: $($state.last_notified_at)" -ForegroundColor Gray
            Write-Host "state_last_status: $($state.last_status)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse notify state file: $stateFile" -ForegroundColor Yellow
        }
    }

    $latestFailureCategory = ''
    $latestFailureNotifyAttempted = $null
    $latestFailureNotified = $null
    $latestFailureSuppressedReason = ''
    $historyFile = [string]$cfg.history_file
    if (-not [string]::IsNullOrWhiteSpace($historyFile) -and (Test-Path $historyFile)) {
        try {
            $historyLast = Get-Content -Path $historyFile -Tail 1 | ConvertFrom-Json
            $latestFailureCategory = [string]$historyLast.failure_category
            $latestFailureNotifyAttempted = $historyLast.failure_notify_attempted
            $latestFailureNotified = $historyLast.failure_notified
            $latestFailureSuppressedReason = [string]$historyLast.failure_notify_suppressed_reason
        }
        catch {
            Write-Host "[WARN] Failed to parse history tail: $historyFile" -ForegroundColor Yellow
        }
    }

    $latestFile = [string]$cfg.log_file
    if (-not [string]::IsNullOrWhiteSpace($latestFile) -and (Test-Path $latestFile)) {
        try {
            $latest = Get-Content -Path $latestFile -Raw | ConvertFrom-Json

            $hasLegacyFields = (-not [string]::IsNullOrWhiteSpace([string]$latest.generated_at)) -or ($null -ne $latest.route) -or ($null -ne $latest.overall)
            $hasCurrentFields = (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) -or ($null -ne $latest.unified_api) -or ($null -ne $latest.comfyui)
            $latestSourceSchema = 'unknown'
            if ($hasLegacyFields -and $hasCurrentFields) {
                $latestSourceSchema = 'mixed'
            }
            elseif ($hasLegacyFields) {
                $latestSourceSchema = 'legacy'
            }
            elseif ($hasCurrentFields) {
                $latestSourceSchema = 'current'
            }

            $latestTs = [string]$latest.generated_at
            if ([string]::IsNullOrWhiteSpace($latestTs)) {
                $latestTs = [string]$latest.ts
            }
            if ([string]::IsNullOrWhiteSpace($latestTs)) {
                $latestTs = 'N/A'
            }

            $latestRouteCategory = [string]$latest.route.category
            if ([string]::IsNullOrWhiteSpace($latestRouteCategory)) {
                $latestUnifiedReady = $false
                $latestDirectReady = $false
                if ($null -ne $latest.unified_api -and $null -ne $latest.unified_api.ready) {
                    try { $latestUnifiedReady = [bool]$latest.unified_api.ready } catch { $latestUnifiedReady = $false }
                }
                if ($null -ne $latest.comfyui -and $null -ne $latest.comfyui.ready) {
                    try { $latestDirectReady = [bool]$latest.comfyui.ready } catch { $latestDirectReady = $false }
                }

                if ($latestUnifiedReady) {
                    $latestRouteCategory = 'unified_ready'
                }
                elseif ($latestDirectReady) {
                    $latestRouteCategory = 'direct_fallback'
                }
                else {
                    $latestRouteCategory = 'pipeline_down'
                }
            }

            $latestOverallOk = $null
            if ($null -ne $latest.overall -and $null -ne $latest.overall.ok) {
                try { $latestOverallOk = [bool]$latest.overall.ok } catch { $latestOverallOk = $null }
            }
            elseif ($null -ne $latest.unified_api -or $null -ne $latest.comfyui) {
                $latestUnifiedReadyForOk = $false
                $latestDirectReadyForOk = $false
                if ($null -ne $latest.unified_api -and $null -ne $latest.unified_api.ready) {
                    try { $latestUnifiedReadyForOk = [bool]$latest.unified_api.ready } catch { $latestUnifiedReadyForOk = $false }
                }
                if ($null -ne $latest.comfyui -and $null -ne $latest.comfyui.ready) {
                    try { $latestDirectReadyForOk = [bool]$latest.comfyui.ready } catch { $latestDirectReadyForOk = $false }
                }
                $latestOverallOk = ($latestUnifiedReadyForOk -or $latestDirectReadyForOk)
            }

            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_source_schema: $latestSourceSchema" -ForegroundColor Gray
            Write-Host "latest_ts: $latestTs" -ForegroundColor Gray
            Write-Host "latest_route_category: $latestRouteCategory" -ForegroundColor Gray
            Write-Host "latest_overall_ok: $latestOverallOk" -ForegroundColor Gray
            Write-Host "latest_ok: $latestOverallOk" -ForegroundColor Gray
            Write-Host "latest_failure_category: $latestFailureCategory" -ForegroundColor Gray
            Write-Host "latest_failure_notify_attempted: $latestFailureNotifyAttempted" -ForegroundColor Gray
            Write-Host "latest_failure_notified: $latestFailureNotified" -ForegroundColor Gray
            Write-Host "latest_failure_notify_suppressed_reason: $latestFailureSuppressedReason" -ForegroundColor Gray
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
