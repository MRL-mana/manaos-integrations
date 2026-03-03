param(
    [int[]]$Checkpoints = @(1500, 4500),
    [int]$StaleMinutes = 20,
    [ValidateSet('latest-wins', 'strict')]
    [string]$StalePolicy = 'latest-wins',
    [switch]$AsJson,
    [string]$OutputPath = '',
    [switch]$NoWrite
)

$ErrorActionPreference = 'Stop'

if ($StaleMinutes -lt 1) { $StaleMinutes = 1 }
if ($StaleMinutes -gt 1440) { $StaleMinutes = 1440 }

$root = $PSScriptRoot
$logDir = Join-Path $root 'logs'

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $logDir 'v114_monitor_summary_latest.json'
}

function Parse-MonitorLog {
    param(
        [string]$FilePath,
        [int]$Checkpoint,
        [int]$StaleMinutesValue
    )

    $item = Get-Item -LiteralPath $FilePath -ErrorAction Stop
    $lines = Get-Content -LiteralPath $FilePath -ErrorAction SilentlyContinue

    $startAt = $null
    $lastTs = $null
    $waitingCount = 0
    $triggerDetected = $false
    $evalRunning = $false
    $evalLaunched = $false
    $unknownLineCount = 0
    $lastEvent = ''

    foreach ($line in $lines) {
        if ($line -notmatch '^\[(?<ts>[^\]]+)\]\s+(?<msg>.+)$') {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $unknownLineCount++
            }
            continue
        }

        $tsValue = $matches['ts']
        $msg = [string]$matches['msg']
        [datetime]$parsedTs = [datetime]::MinValue
        if ([datetime]::TryParse($tsValue, [ref]$parsedTs)) {
            if (-not $startAt -and $msg -like 'watch start:*') {
                $startAt = $parsedTs
            }
            $lastTs = $parsedTs
        }

        $lastEvent = $msg
        if ($msg -eq 'waiting...') {
            $waitingCount++
            continue
        }
        if ($msg -match '\[TRIGGER_DETECTED\]' -or $msg -match 'checkpoint-\d+\s+exists') {
            $triggerDetected = $true
            continue
        }
        if ($msg -like 'running layer2 quick eval:*') {
            $evalRunning = $true
            continue
        }
        if ($msg -like 'launched eval pid=*') {
            $evalLaunched = $true
            continue
        }
        if ($msg -notlike 'watch start:*') {
            $unknownLineCount++
        }
    }

    $now = Get-Date
    $lastRef = if ($lastTs) { $lastTs } else { $item.LastWriteTime }
    $ageSec = [int][Math]::Round(($now - $lastRef).TotalSeconds, 0)
    $isStale = $ageSec -gt ($StaleMinutesValue * 60)

    $status = 'unknown'
    if ($evalLaunched) {
        $status = 'eval_launched'
    }
    elseif ($evalRunning -or $triggerDetected) {
        $status = 'triggered'
    }
    elseif ($waitingCount -gt 0) {
        $status = 'waiting'
    }
    elseif ($startAt) {
        $status = 'started'
    }

    if ($isStale -and $status -in @('waiting', 'started')) {
        $status = 'stale'
    }

    return [ordered]@{
        checkpoint = $Checkpoint
        status = $status
        stale = $isStale
        stale_threshold_minutes = $StaleMinutesValue
        latest_log = $FilePath
        log_last_write_time = $item.LastWriteTime.ToString('o')
        start_time = if ($startAt) { $startAt.ToString('o') } else { $null }
        last_event_time = if ($lastTs) { $lastTs.ToString('o') } else { $null }
        last_event = $lastEvent
        waiting_count = $waitingCount
        trigger_detected = $triggerDetected
        eval_running = $evalRunning
        eval_launched = $evalLaunched
        unknown_line_count = $unknownLineCount
        age_sec = $ageSec
    }
}

$results = @()
foreach ($checkpoint in $Checkpoints) {
    $latest = Get-ChildItem -Path $logDir -File -Filter ("monitor_v114_ck{0}_*.log" -f $checkpoint) -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        $results += [ordered]@{
            checkpoint = [int]$checkpoint
            status = 'missing'
            stale = $true
            stale_threshold_minutes = $StaleMinutes
            latest_log = $null
            log_last_write_time = $null
            start_time = $null
            last_event_time = $null
            last_event = $null
            waiting_count = 0
            trigger_detected = $false
            eval_running = $false
            eval_launched = $false
            unknown_line_count = 0
            age_sec = $null
        }
        continue
    }

    $results += Parse-MonitorLog -FilePath $latest.FullName -Checkpoint $checkpoint -StaleMinutesValue $StaleMinutes
}

$overall = 'healthy'
$ignoredStaleCheckpoints = @()
$activeCheckpoint = $null

$latestResult = $results |
    Sort-Object { [int]$_.checkpoint } -Descending |
    Select-Object -First 1

$latestHealthyStatuses = @('waiting', 'triggered', 'eval_launched', 'started')
$latestIsHealthy = $false
if ($latestResult) {
    $activeCheckpoint = [int]$latestResult.checkpoint
    $latestIsHealthy = ($latestResult.status -in $latestHealthyStatuses) -and (-not [bool]$latestResult.stale)
}

$effectiveStaleResults = @($results | Where-Object { $_.status -eq 'stale' })
if ($StalePolicy -eq 'latest-wins' -and $latestIsHealthy) {
    $effectiveStaleResults = @(
        $effectiveStaleResults |
            Where-Object { [int]$_.checkpoint -ge [int]$activeCheckpoint }
    )
    $ignoredStaleCheckpoints = @(
        $results |
            Where-Object { $_.status -eq 'stale' -and [int]$_.checkpoint -lt [int]$activeCheckpoint } |
            ForEach-Object { [int]$_.checkpoint }
    )
}

if (($results | Where-Object { $_.status -eq 'missing' }).Count -gt 0) {
    $overall = 'degraded'
}
elseif ($effectiveStaleResults.Count -gt 0) {
    $overall = 'stale'
}
elseif (($results | Where-Object { $_.status -eq 'unknown' }).Count -gt 0) {
    $overall = 'warning'
}

$summary = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    overall = $overall
    stale_policy = $StalePolicy
    active_checkpoint = $activeCheckpoint
    ignored_stale_checkpoints = @($ignoredStaleCheckpoints)
    checkpoints = @($results)
}

if (-not $NoWrite) {
    $parent = Split-Path -Parent $OutputPath
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $OutputPath -Encoding UTF8
}

if ($AsJson) {
    $summary | ConvertTo-Json -Depth 8
    exit 0
}

Write-Host '=== v1.1.4 monitor summary (ck1500/ck4500) ===' -ForegroundColor Cyan
Write-Host ("overall: {0}" -f $summary.overall) -ForegroundColor DarkGray
foreach ($r in $summary.checkpoints) {
    Write-Host ("- ck{0}: status={1} stale={2} age_sec={3} waits={4}" -f $r.checkpoint, $r.status, $r.stale, $r.age_sec, $r.waiting_count)
    if ($r.latest_log) {
        Write-Host ("  log: {0}" -f $r.latest_log) -ForegroundColor DarkGray
    }
}
if (-not $NoWrite) {
    Write-Host ("written: {0}" -f $OutputPath) -ForegroundColor DarkGray
}

exit 0