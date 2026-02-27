param(
    [string]$TaskName = "ManaOS_Reason_Enum_Lint_Cooldown_Verify_Weekly",
    [string]$ConfigFile = "",
    [string]$LatestJsonFile = "",
    [string]$NotifyStateFile = "",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-SchtasksLastResultMeaning {
    param([int]$Code)

    switch ($Code) {
        0 { return "success" }
        267008 { return "task_ready" }
        267009 { return "task_running" }
        267010 { return "task_disabled" }
        267011 { return "task_has_not_run_yet" }
        267012 { return "task_no_more_runs" }
        267013 { return "task_not_scheduled" }
        267014 { return "task_terminated" }
        267015 { return "task_no_valid_triggers" }
        267016 { return "task_event_trigger" }
        default { return "unknown_or_error" }
    }
}

function Get-TaskDerivedLatestOkReason {
    param([int]$Code)

    switch ($Code) {
        0 { return 'lint_passed' }
        267010 { return 'task_disabled' }
        267011 { return 'task_not_run_yet' }
        267013 { return 'task_not_scheduled' }
        default { return 'task_last_result_error' }
    }
}

function Get-SchtasksListValue {
    param(
        [string[]]$Lines,
        [string]$Pattern
    )

    $line = $Lines | Where-Object { $_ -match $Pattern } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($line)) {
        return ""
    }
    $parts = $line -split ':', 2
    if ($parts.Count -lt 2) {
        return ""
    }
    return [string]$parts[1].Trim()
}

$taskDerivedLatestOkReason = ''
$taskDerivedLatestOk = $false

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($LatestJsonFile) -and -not [string]::IsNullOrWhiteSpace([string]$cfg.latest_json_file)) {
            $LatestJsonFile = [string]$cfg.latest_json_file
        }
        if ([string]::IsNullOrWhiteSpace($NotifyStateFile) -and -not [string]::IsNullOrWhiteSpace([string]$cfg.notify_state_file)) {
            $NotifyStateFile = [string]$cfg.notify_state_file
        }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_lint.latest.json"
}
if ([string]::IsNullOrWhiteSpace($NotifyStateFile)) {
    $NotifyStateFile = Join-Path $scriptDir "logs\reason_enum_lint_notify_state.json"
}

if ($AsJson) {
    $payload = [ordered]@{
        task_name = $TaskName
        config_file = $ConfigFile
        task_found = $false
        task_to_run = ""
        task_last_result_code = $null
        task_last_result_hex = ""
        task_last_result_meaning = ""
        task_last_result_latest_ok = $false
        task_last_result_latest_ok_reason = ""
        latest_json_file = $LatestJsonFile
        notify_state_file = $NotifyStateFile
        latest_ts = 'N/A'
        latest_ok = $false
        latest_ok_reason = 'source_missing'
        latest_ok_reason_bridge = ""
        latest_failure_category = ""
        latest_failure_notify_attempted = $false
        latest_failure_notified = $false
        latest_failure_notify_suppressed_reason = 'source_missing'
        state_last_failure_notified_at = ""
        state_last_status = ""
        state_updated_at = ""
    }

    $taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
    if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
        $payload.latest_ok_reason = 'task_not_found'
        $payload.latest_failure_notify_suppressed_reason = 'task_not_found'
        $payloadJson = ($payload | ConvertTo-Json -Depth 8)
        Write-Output $payloadJson
        exit 1
    }

    $payload.task_found = $true
    $payload.task_to_run = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Task To Run|実行するタスク):\s*'
    $taskLastResultRaw = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Last Result|前回の結果):\s*'
    if (-not [string]::IsNullOrWhiteSpace($taskLastResultRaw)) {
        $taskLastResultCode = 0
        if ([int]::TryParse($taskLastResultRaw, [ref]$taskLastResultCode)) {
            $payload.task_last_result_code = $taskLastResultCode
            $payload.task_last_result_hex = ('0x{0:X8}' -f [uint32]$taskLastResultCode)
            $payload.task_last_result_meaning = Get-SchtasksLastResultMeaning -Code $taskLastResultCode
            $payload.task_last_result_latest_ok = ($taskLastResultCode -eq 0)
            $payload.task_last_result_latest_ok_reason = Get-TaskDerivedLatestOkReason -Code $taskLastResultCode
        }
    }

    if (Test-Path $LatestJsonFile) {
        try {
            $latest = Get-Content -Path $LatestJsonFile -Raw | ConvertFrom-Json
            $payload.latest_ts = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
            $payload.latest_ok = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
            $payload.latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
            $payload.latest_failure_category = [string]$latest.failure_category
            $payload.latest_failure_notify_attempted = if ($null -ne $latest.failure_notify_attempted) { [bool]$latest.failure_notify_attempted } else { $false }
            $payload.latest_failure_notified = if ($null -ne $latest.failure_notified) { [bool]$latest.failure_notified } else { $false }
            $payload.latest_failure_notify_suppressed_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.failure_notify_suppressed_reason)) { [string]$latest.failure_notify_suppressed_reason } else { '' }
        }
        catch {
            $payload.latest_ok = $false
            $payload.latest_ok_reason = 'source_missing'
            $payload.latest_failure_notify_suppressed_reason = 'source_missing'
        }
    }

    if ($payload.latest_ok_reason -eq 'source_missing' -and -not [string]::IsNullOrWhiteSpace([string]$payload.task_last_result_latest_ok_reason)) {
        $payload.latest_ok_reason_bridge = [string]$payload.task_last_result_latest_ok_reason
    }

    if (Test-Path $NotifyStateFile) {
        try {
            $state = Get-Content -Path $NotifyStateFile -Raw | ConvertFrom-Json
            $payload.state_last_failure_notified_at = [string]$state.last_failure_notified_at
            $payload.state_last_status = [string]$state.last_status
            $payload.state_updated_at = [string]$state.updated_at
        }
        catch {
        }
    }

    $payloadJson = ($payload | ConvertTo-Json -Depth 8)
    Write-Output $payloadJson
    exit 0
}

Write-Host "=== Reason Enum Cooldown Verify Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
Write-Host "ConfigFile: $ConfigFile" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: task_not_found" -ForegroundColor Gray
    Write-Host "latest_failure_notify_suppressed_reason: source_missing" -ForegroundColor Gray
    exit 1
}

$taskInfo | ForEach-Object { Write-Host $_ }

$taskToRunLine = $taskInfo | Where-Object { $_ -match '^(Task To Run|実行するタスク):\s*' } | Select-Object -First 1
if (-not [string]::IsNullOrWhiteSpace($taskToRunLine)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $taskToRunLine" -ForegroundColor Gray
}

$taskLastResultLine = $taskInfo | Where-Object { $_ -match '^(Last Result|前回の結果):\s*' } | Select-Object -First 1
if (-not [string]::IsNullOrWhiteSpace($taskLastResultLine)) {
    $taskLastResultRaw = [string](($taskLastResultLine -split ':', 2)[1]).Trim()
    $taskLastResultCode = 0
    if ([int]::TryParse($taskLastResultRaw, [ref]$taskLastResultCode)) {
        $taskLastResultHex = ('0x{0:X8}' -f [uint32]$taskLastResultCode)
        $taskLastResultMeaning = Get-SchtasksLastResultMeaning -Code $taskLastResultCode
        $taskDerivedLatestOkReason = Get-TaskDerivedLatestOkReason -Code $taskLastResultCode
        $taskDerivedLatestOk = ($taskLastResultCode -eq 0)
        Write-Host "task_last_result_code: $taskLastResultCode" -ForegroundColor Gray
        Write-Host "task_last_result_hex: $taskLastResultHex" -ForegroundColor Gray
        Write-Host "task_last_result_meaning: $taskLastResultMeaning" -ForegroundColor Gray
        Write-Host "task_last_result_latest_ok: $taskDerivedLatestOk" -ForegroundColor Gray
        Write-Host "task_last_result_latest_ok_reason: $taskDerivedLatestOkReason" -ForegroundColor Gray
    }
    else {
        Write-Host "task_last_result_raw: $taskLastResultRaw" -ForegroundColor Gray
    }
}

Write-Host "LatestJsonFile: $LatestJsonFile" -ForegroundColor Gray
if (Test-Path $LatestJsonFile) {
    try {
        $latest = Get-Content -Path $LatestJsonFile -Raw | ConvertFrom-Json
        $latestTs = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
        $latestOk = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
        $latestOkReason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
        $latestSuppressed = if (-not [string]::IsNullOrWhiteSpace([string]$latest.failure_notify_suppressed_reason)) { [string]$latest.failure_notify_suppressed_reason } else { '' }

        Write-Host "--- Latest Output ---" -ForegroundColor Cyan
        Write-Host "latest_ts: $latestTs" -ForegroundColor Gray
        Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
        Write-Host "latest_ok_reason: $latestOkReason" -ForegroundColor Gray
        if ($latestOkReason -eq 'source_missing' -and -not [string]::IsNullOrWhiteSpace($taskDerivedLatestOkReason)) {
            Write-Host "latest_ok_reason_bridge: $taskDerivedLatestOkReason" -ForegroundColor Gray
        }
        Write-Host "latest_failure_category: $($latest.failure_category)" -ForegroundColor Gray
        Write-Host "latest_failure_notify_attempted: $($latest.failure_notify_attempted)" -ForegroundColor Gray
        Write-Host "latest_failure_notified: $($latest.failure_notified)" -ForegroundColor Gray
        Write-Host "latest_failure_notify_suppressed_reason: $latestSuppressed" -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Failed to parse latest output file: $LatestJsonFile" -ForegroundColor Yellow
        Write-Host "--- Latest Output ---" -ForegroundColor Cyan
        Write-Host "latest_ts: N/A" -ForegroundColor Gray
        Write-Host "latest_ok: False" -ForegroundColor Gray
        Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
        if (-not [string]::IsNullOrWhiteSpace($taskDerivedLatestOkReason)) {
            Write-Host "latest_ok_reason_bridge: $taskDerivedLatestOkReason" -ForegroundColor Gray
        }
        Write-Host "latest_failure_notify_suppressed_reason: source_missing" -ForegroundColor Gray
    }
}
else {
    Write-Host "[WARN] Latest output file not found: $LatestJsonFile" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: False" -ForegroundColor Gray
    Write-Host "latest_ok_reason: source_missing" -ForegroundColor Gray
    if (-not [string]::IsNullOrWhiteSpace($taskDerivedLatestOkReason)) {
        Write-Host "latest_ok_reason_bridge: $taskDerivedLatestOkReason" -ForegroundColor Gray
    }
    Write-Host "latest_failure_notify_suppressed_reason: source_missing" -ForegroundColor Gray
}

Write-Host "NotifyStateFile: $NotifyStateFile" -ForegroundColor Gray
if (Test-Path $NotifyStateFile) {
    try {
        $state = Get-Content -Path $NotifyStateFile -Raw | ConvertFrom-Json
        Write-Host "--- Notify State ---" -ForegroundColor Cyan
        Write-Host "state_last_failure_notified_at: $($state.last_failure_notified_at)" -ForegroundColor Gray
        Write-Host "state_last_status: $($state.last_status)" -ForegroundColor Gray
        Write-Host "state_updated_at: $($state.updated_at)" -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Failed to parse notify state file: $NotifyStateFile" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[WARN] Notify state file not found: $NotifyStateFile" -ForegroundColor Yellow
}

exit 0
