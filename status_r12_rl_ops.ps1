param(
    [switch]$Json,
    [string]$JsonOutFile = "",
    [int]$TailLines = 20,
    [int]$MaxR12LogAgeMinutes = 30
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$r12Status = Join-Path $scriptDir "status_r12_health_watch_task.ps1"
$rlStatus = Join-Path $scriptDir "status_rl_anything_bootstrap_task.ps1"
$opsWatchStatus = Join-Path $scriptDir "status_r12_rl_ops_watch_task.ps1"
$r12Log = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"
$rlConfig = Join-Path $scriptDir "logs\rl_anything_bootstrap_task.config.json"
$opsWatchConfig = Join-Path $scriptDir "logs\r12_rl_ops_watch_task.config.json"

function Get-QueryValue {
    param(
        [string[]]$Names,
        [string[]]$Lines
    )

    foreach ($name in $Names) {
        $line = $Lines | Where-Object { $_ -match ("^" + [regex]::Escape($name) + "\s*:") } | Select-Object -First 1
        if ($null -ne $line) {
            return (($line -split ":", 2)[1]).Trim()
        }
    }

    return ""
}

function Get-TaskConfigStatus {
    param(
        [string]$TaskToRun,
        [string]$DefaultConfigFile
    )

    $issues = New-Object System.Collections.Generic.List[string]
    $configPath = ""
    $hasConfigArg = $false

    if (-not [string]::IsNullOrWhiteSpace($TaskToRun)) {
        $match = [regex]::Match($TaskToRun, '-ConfigFile\s+(?:"([^"]+)"|''([^'']+)''|(\S+))', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($match.Success) {
            $hasConfigArg = $true
            if (-not [string]::IsNullOrWhiteSpace($match.Groups[1].Value)) {
                $configPath = $match.Groups[1].Value
            }
            elseif (-not [string]::IsNullOrWhiteSpace($match.Groups[2].Value)) {
                $configPath = $match.Groups[2].Value
            }
            elseif (-not [string]::IsNullOrWhiteSpace($match.Groups[3].Value)) {
                $configPath = $match.Groups[3].Value
            }
        }
    }

    if (-not $hasConfigArg) {
        $issues.Add("Task command does not include -ConfigFile")
        $configPath = $DefaultConfigFile
    }

    if ([string]::IsNullOrWhiteSpace($configPath)) {
        $issues.Add("Config file path is empty")
        return @{
            hasConfigArg = $hasConfigArg
            configPath = $configPath
            configExists = $false
            configParseOk = $false
            issues = @($issues)
        }
    }

    $exists = Test-Path $configPath
    if (-not $exists) {
        $issues.Add("Config file not found: $configPath")
    }

    $parseOk = $false
    if ($exists) {
        try {
            $null = Get-Content -Path $configPath -Raw | ConvertFrom-Json
            $parseOk = $true
        }
        catch {
            $issues.Add("Config file parse failed: $configPath")
        }
    }

    return @{
        hasConfigArg = $hasConfigArg
        configPath = $configPath
        configExists = $exists
        configParseOk = $parseOk
        issues = @($issues)
    }
}

function Get-TaskSnapshot {
    param(
        [string]$TaskName,
        [switch]$RequireConfigFile,
        [string]$DefaultConfigFile = ""
    )

    $queryLines = schtasks /Query /TN $TaskName /V /FO LIST 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{
            taskName = $TaskName
            exists = $false
            isHealthy = $false
            issues = @("Task not found: $TaskName")
        }
    }

    $state = Get-QueryValue -Names @("状態", "Status") -Lines $queryLines
    $lastResult = Get-QueryValue -Names @("前回の結果", "Last Result") -Lines $queryLines
    $nextRun = Get-QueryValue -Names @("次回の実行時刻", "Next Run Time") -Lines $queryLines
    $lastRun = Get-QueryValue -Names @("前回の実行時刻", "Last Run Time") -Lines $queryLines
    $taskToRun = Get-QueryValue -Names @("実行するタスク", "Task To Run") -Lines $queryLines

    $issues = New-Object System.Collections.Generic.List[string]
    if ($state -and ($state -notin @("準備完了", "実行中", "Ready", "Running"))) {
        $issues.Add("Task state is not healthy: $state")
    }
    if ($lastResult -and ($lastResult -notin @("0", "0x0", "267009", "267011"))) {
        $issues.Add("Last result indicates failure: $lastResult")
    }

    $configStatus = $null
    if ($RequireConfigFile.IsPresent) {
        $configStatus = Get-TaskConfigStatus -TaskToRun $taskToRun -DefaultConfigFile $DefaultConfigFile
        foreach ($issue in @($configStatus.issues)) {
            $issues.Add($issue)
        }
    }

    return @{
        taskName = $TaskName
        exists = $true
        state = $state
        lastResult = $lastResult
        nextRun = $nextRun
        lastRun = $lastRun
        taskToRun = $taskToRun
        configStatus = $configStatus
        isHealthy = ($issues.Count -eq 0)
        issues = @($issues)
    }
}

function Get-R12LogSnapshot {
    param(
        [string]$LogPath,
        [int]$TailCount,
        [int]$MaxLogAgeMinutes
    )

    if (-not (Test-Path $LogPath)) {
        return @{
            exists = $false
            issues = @("Log file not found: $LogPath")
        }
    }

    $tail = Get-Content $LogPath -Tail $TailCount
    $latest = $null
    $lastLogAgeMinutes = $null
    $issues = New-Object System.Collections.Generic.List[string]
    $latestLine = Get-Content $LogPath -Tail 1
    if (-not [string]::IsNullOrWhiteSpace($latestLine)) {
        try {
            $latest = $latestLine | ConvertFrom-Json
            if ($null -ne $latest.failed -and [int]$latest.failed -gt 0) {
                $issues.Add("Latest log has failed endpoints: $($latest.failed)")
            }
            if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) {
                $latestTs = [datetimeoffset]::Parse([string]$latest.ts)
                $age = ([datetimeoffset]::Now - $latestTs).TotalMinutes
                $lastLogAgeMinutes = [math]::Round($age, 1)
                if ($age -gt $MaxLogAgeMinutes) {
                    $issues.Add(("Latest log is stale: {0:N1} min old" -f $age))
                }
            }
        } catch {
            $issues.Add("Failed to parse latest log line as JSON")
        }
    } else {
        $issues.Add("Log file is empty")
    }

    return @{
        exists = $true
        tail = @($tail)
        latest = $latest
        lastLogAgeMinutes = $lastLogAgeMinutes
        isHealthy = ($issues.Count -eq 0)
        issues = @($issues)
    }
}

function Get-OpsWatchSnapshot {
    param(
        [string]$ConfigPath
    )

    $issues = New-Object System.Collections.Generic.List[string]
    $result = [ordered]@{
        configPath = $ConfigPath
        configExists = $false
        configParseOk = $false
        summaryLogPath = ""
        stateFile = ""
        latestSummary = $null
        notifyState = $null
        issues = @()
    }

    if (-not (Test-Path $ConfigPath)) {
        $issues.Add("Ops watch config not found: $ConfigPath")
        $result.issues = @($issues)
        return $result
    }

    $result.configExists = $true
    $cfg = $null
    try {
        $cfg = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        $result.configParseOk = $true
    }
    catch {
        $issues.Add("Ops watch config parse failed: $ConfigPath")
        $result.issues = @($issues)
        return $result
    }

    $summaryLogPath = [string]$cfg.summary_log_path
    $stateFile = [string]$cfg.degraded_state_file
    $result.summaryLogPath = $summaryLogPath
    $result.stateFile = $stateFile

    if ([string]::IsNullOrWhiteSpace($summaryLogPath)) {
        $issues.Add("Ops watch summary_log_path is empty")
    }
    elseif (-not (Test-Path $summaryLogPath)) {
        $issues.Add("Ops watch summary log not found: $summaryLogPath")
    }
    else {
        try {
            $latestSummaryLine = Get-Content -Path $summaryLogPath -Tail 1
            if (-not [string]::IsNullOrWhiteSpace($latestSummaryLine)) {
                $result.latestSummary = $latestSummaryLine | ConvertFrom-Json
            }
            else {
                $issues.Add("Ops watch summary log is empty: $summaryLogPath")
            }
        }
        catch {
            $issues.Add("Ops watch summary log parse failed: $summaryLogPath")
        }
    }

    if ([string]::IsNullOrWhiteSpace($stateFile)) {
        $issues.Add("Ops watch degraded_state_file is empty")
    }
    elseif (-not (Test-Path $stateFile)) {
        $issues.Add("Ops watch state file not found: $stateFile")
    }
    else {
        try {
            $result.notifyState = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
        }
        catch {
            $issues.Add("Ops watch state file parse failed: $stateFile")
        }
    }

    $result.issues = @($issues)
    return $result
}

function Write-ConfigLinkSummary {
    param(
        [string]$Label,
        $TaskSnapshot
    )

    if ($null -eq $TaskSnapshot -or -not $TaskSnapshot.exists) {
        Write-Host "[WARN] $Label config linkage: task missing" -ForegroundColor Yellow
        return
    }

    $cfg = $TaskSnapshot.configStatus
    if ($null -eq $cfg) {
        Write-Host "[WARN] $Label config linkage: not checked" -ForegroundColor Yellow
        return
    }

    $cfgIssues = @($cfg.issues)
    if ($cfgIssues.Count -eq 0) {
        Write-Host "[OK] $Label config linkage: OK | path=$($cfg.configPath)" -ForegroundColor Green
        return
    }

    $issueText = $cfgIssues -join '; '
    Write-Host "[WARN] $Label config linkage: WARN | path=$($cfg.configPath) | issues=$issueText" -ForegroundColor Yellow
}

if ($Json.IsPresent) {
    $r12Task = Get-TaskSnapshot -TaskName "ManaOS_R12_Health_Watch_5min"
    $rlTask = Get-TaskSnapshot -TaskName "ManaOS_RLAnything_Bootstrap_Logon" -RequireConfigFile -DefaultConfigFile $rlConfig
    $opsWatchTask = Get-TaskSnapshot -TaskName "ManaOS_R12_RL_Ops_Watch_15min" -RequireConfigFile -DefaultConfigFile $opsWatchConfig
    $r12LogSnapshot = Get-R12LogSnapshot -LogPath $r12Log -TailCount $TailLines -MaxLogAgeMinutes $MaxR12LogAgeMinutes
    $opsWatchSnapshot = Get-OpsWatchSnapshot -ConfigPath $opsWatchConfig

    $allIssues = @($r12Task.issues) + @($rlTask.issues) + @($opsWatchTask.issues) + @($r12LogSnapshot.issues) + @($opsWatchSnapshot.issues)
    $payload = @{
        ok = ($allIssues.Count -eq 0)
        checkedAt = [datetimeoffset]::Now.ToString("o")
        r12Task = $r12Task
        rlTask = $rlTask
        opsWatchTask = $opsWatchTask
        opsWatch = $opsWatchSnapshot
        r12Log = @{
            path = $r12Log
            exists = $r12LogSnapshot.exists
            latest = $r12LogSnapshot.latest
            tail = $r12LogSnapshot.tail
            lastLogAgeMinutes = $r12LogSnapshot.lastLogAgeMinutes
            isHealthy = $r12LogSnapshot.isHealthy
            issues = $r12LogSnapshot.issues
        }
        issues = $allIssues
    }

    $jsonText = ($payload | ConvertTo-Json -Depth 8)
    if (-not [string]::IsNullOrWhiteSpace($JsonOutFile)) {
        $jsonDir = Split-Path -Parent $JsonOutFile
        if (-not [string]::IsNullOrWhiteSpace($jsonDir) -and -not (Test-Path $jsonDir)) {
            New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
        }
        Set-Content -Path $JsonOutFile -Value $jsonText -Encoding UTF8
    }
    Write-Output $jsonText
    if ($payload.ok) { exit 0 }
    exit 1
}

Write-Host "=== Combined Ops Status (R12 + RL) ===" -ForegroundColor Cyan

pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Status
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlStatus
pwsh -NoProfile -ExecutionPolicy Bypass -File $opsWatchStatus

$rlTaskSnapshot = Get-TaskSnapshot -TaskName "ManaOS_RLAnything_Bootstrap_Logon" -RequireConfigFile -DefaultConfigFile $rlConfig
$opsWatchTaskSnapshot = Get-TaskSnapshot -TaskName "ManaOS_R12_RL_Ops_Watch_15min" -RequireConfigFile -DefaultConfigFile $opsWatchConfig
$opsWatchSnapshot = Get-OpsWatchSnapshot -ConfigPath $opsWatchConfig

Write-Host ""
Write-Host "=== Config Linkage Summary ===" -ForegroundColor Cyan
Write-ConfigLinkSummary -Label "RLAnything" -TaskSnapshot $rlTaskSnapshot
Write-ConfigLinkSummary -Label "R12+RL Ops Watch" -TaskSnapshot $opsWatchTaskSnapshot

Write-Host ""
Write-Host "=== Ops Watch Latest Output ===" -ForegroundColor Cyan
if ($null -ne $opsWatchSnapshot.latestSummary) {
    $latestTs = [string]$opsWatchSnapshot.latestSummary.ts
    if ([string]::IsNullOrWhiteSpace($latestTs)) {
        $latestTs = 'N/A'
    }
    $latestOk = $null
    $latestOkReason = 'ok_missing'
    if ($null -ne $opsWatchSnapshot.latestSummary.ok) {
        try { $latestOk = [bool]$opsWatchSnapshot.latestSummary.ok } catch { $latestOk = $null }
        if ($null -ne $latestOk) { $latestOkReason = 'from_ok_field' }
    }
    elseif ($null -ne $opsWatchSnapshot.latestSummary.issues) {
        try {
            $latestOk = (@($opsWatchSnapshot.latestSummary.issues).Count -eq 0)
            $latestOkReason = 'from_issues_count'
        }
        catch { $latestOk = $null }
    }
    elseif ($null -ne $opsWatchSnapshot.latestSummary.r12_latest_failed) {
        try {
            $latestOk = ([int]$opsWatchSnapshot.latestSummary.r12_latest_failed -eq 0)
            $latestOkReason = 'from_r12_latest_failed'
        }
        catch { $latestOk = $null }
    }
    elseif (-not [string]::IsNullOrWhiteSpace([string]$opsWatchSnapshot.latestSummary.failure_category)) {
        $latestOk = $false
        $latestOkReason = 'from_failure_category'
    }

    $latestFailureCategory = [string]$opsWatchSnapshot.latestSummary.failure_category
    $latestFailureNotifyAttempted = $null
    if ($null -ne $opsWatchSnapshot.latestSummary.failure_notify_attempted) {
        try { $latestFailureNotifyAttempted = [bool]$opsWatchSnapshot.latestSummary.failure_notify_attempted } catch { $latestFailureNotifyAttempted = $null }
    }
    $latestFailureNotified = $null
    if ($null -ne $opsWatchSnapshot.latestSummary.failure_notified) {
        try { $latestFailureNotified = [bool]$opsWatchSnapshot.latestSummary.failure_notified } catch { $latestFailureNotified = $null }
    }
    $latestFailureSuppressedReason = [string]$opsWatchSnapshot.latestSummary.failure_notify_suppressed_reason

    $latestDegradedNotifyAttempted = $null
    if ($null -ne $opsWatchSnapshot.latestSummary.degraded_notify_attempted) {
        try { $latestDegradedNotifyAttempted = [bool]$opsWatchSnapshot.latestSummary.degraded_notify_attempted } catch { $latestDegradedNotifyAttempted = $null }
    }
    $latestDegradedNotified = $null
    if ($null -ne $opsWatchSnapshot.latestSummary.degraded_notified) {
        try { $latestDegradedNotified = [bool]$opsWatchSnapshot.latestSummary.degraded_notified } catch { $latestDegradedNotified = $null }
    }
    $latestDegradedSuppressedReason = [string]$opsWatchSnapshot.latestSummary.degraded_notify_suppressed_reason

    Write-Host "latest_ts: $latestTs" -ForegroundColor Gray
    Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
    Write-Host "latest_ok_reason: $latestOkReason" -ForegroundColor Gray
    Write-Host "latest_failure_category: $latestFailureCategory" -ForegroundColor Gray
    Write-Host "latest_failure_notify_attempted: $latestFailureNotifyAttempted" -ForegroundColor Gray
    Write-Host "latest_failure_notified: $latestFailureNotified" -ForegroundColor Gray
    Write-Host "latest_failure_notify_suppressed_reason: $latestFailureSuppressedReason" -ForegroundColor Gray
    Write-Host "latest_degraded_notify_attempted: $latestDegradedNotifyAttempted" -ForegroundColor Gray
    Write-Host "latest_degraded_notified: $latestDegradedNotified" -ForegroundColor Gray
    Write-Host "latest_degraded_notify_suppressed_reason: $latestDegradedSuppressedReason" -ForegroundColor Gray
}
else {
    $opsWatchIssues = @($opsWatchSnapshot.issues)
    if ($opsWatchIssues.Count -gt 0) {
        Write-Host "[WARN] Ops watch latest notify unavailable: $($opsWatchIssues -join '; ')" -ForegroundColor Yellow
    }
    else {
        Write-Host "[INFO] Ops watch latest notify unavailable" -ForegroundColor Yellow
    }
}

if (Test-Path $r12Log) {
    Write-Host "" 
    Write-Host "=== R12 Log Tail (last $TailLines) ===" -ForegroundColor Cyan
    Get-Content $r12Log -Tail $TailLines
} else {
    Write-Host "[INFO] r12 log not found: $r12Log" -ForegroundColor Yellow
}
