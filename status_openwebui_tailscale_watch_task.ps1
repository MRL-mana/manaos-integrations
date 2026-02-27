param(
    [string]$TaskName = "ManaOS_OpenWebUI_Tailscale_Watch_5min",
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

function Test-IsFailureCategory {
    param(
        [string]$Category
    )

    if ([string]::IsNullOrWhiteSpace($Category)) {
        return $false
    }

    $normalized = $Category.Trim().ToLowerInvariant()
    return ($normalized -notin @('none', 'ok', 'healthy', 'success', 'normal'))
}

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

    $stateFile = [string]$cfg.notify_state_file
    if (-not [string]::IsNullOrWhiteSpace($stateFile) -and (Test-Path $stateFile)) {
        try {
            $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
            Write-Host "--- Notify State ---" -ForegroundColor Cyan
            Write-Host "state_last_failure_category: $($state.last_failure_category)" -ForegroundColor Gray
            Write-Host "state_last_failure_notified_at: $($state.last_failure_notified_at)" -ForegroundColor Gray
            Write-Host "state_last_status: $($state.last_status)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse notify state file: $stateFile" -ForegroundColor Yellow
        }
    }

    $latestFile = [string]$cfg.json_out_file
    if (-not [string]::IsNullOrWhiteSpace($latestFile) -and (Test-Path $latestFile)) {
        try {
            $latest = Get-Content -Path $latestFile -Raw | ConvertFrom-Json

            $latestOk = $null
            $latestOkReason = 'ok_missing'
            if ($null -ne $latest.ok) {
                try { $latestOk = [bool]$latest.ok } catch { $latestOk = $null }
                if ($null -ne $latestOk) { $latestOkReason = 'from_ok_field' }
            }
            elseif ($null -ne $latest.issues) {
                try {
                    $latestOk = (@($latest.issues).Count -eq 0)
                    $latestOkReason = 'from_issues_count'
                }
                catch { $latestOk = $null }
            }
            elseif ($null -ne $latest.openwebui_ok -or $null -ne $latest.port_3001_listening -or $null -ne $latest.tailscale_ip) {
                $openwebuiOk = $false
                $portListening = $false
                $tailscaleOk = $false
                if ($null -ne $latest.openwebui_ok) {
                    try { $openwebuiOk = [bool]$latest.openwebui_ok } catch { $openwebuiOk = $false }
                }
                if ($null -ne $latest.port_3001_listening) {
                    try { $portListening = [bool]$latest.port_3001_listening } catch { $portListening = $false }
                }
                if (-not [string]::IsNullOrWhiteSpace([string]$latest.tailscale_ip)) {
                    $tailscaleOk = $true
                }
                $latestOk = ($openwebuiOk -and $portListening -and $tailscaleOk)
                $latestOkReason = 'from_component_fields'
            }
            elseif (Test-IsFailureCategory -Category ([string]$latest.failure_category)) {
                $latestOk = $false
                $latestOkReason = 'from_failure_category'
            }

            $latestTsDisplay = [string]$latest.ts
            if ([string]::IsNullOrWhiteSpace($latestTsDisplay)) {
                $latestTsDisplay = 'N/A'
            }

            Write-Host "--- Latest Output ---" -ForegroundColor Cyan
            Write-Host "latest_ts: $latestTsDisplay" -ForegroundColor Gray
            Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
            Write-Host "latest_ok_reason: $latestOkReason" -ForegroundColor Gray
            Write-Host "latest_failure_category: $($latest.failure_category)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_attempted: $($latest.failure_notify_attempted)" -ForegroundColor Gray
            Write-Host "latest_failure_notified: $($latest.failure_notified)" -ForegroundColor Gray
            Write-Host "latest_failure_notify_suppressed_reason: $($latest.failure_notify_suppressed_reason)" -ForegroundColor Gray
        }
        catch {
            Write-Host "[WARN] Failed to parse latest output file: $latestFile" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "--- Latest Output ---" -ForegroundColor Cyan
        Write-Host "latest_ts: N/A" -ForegroundColor Gray
        Write-Host "latest_ok: " -ForegroundColor Gray
        Write-Host "latest_ok_reason: ok_missing" -ForegroundColor Gray
        if (-not [string]::IsNullOrWhiteSpace($latestFile)) {
            Write-Host "[WARN] Latest output file not found: $latestFile" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
}

exit 0
