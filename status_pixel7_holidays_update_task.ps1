param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual"
)

$ErrorActionPreference = "Stop"

function Test-TaskResultOk {
    param([string]$RawResult)

    if ([string]::IsNullOrWhiteSpace($RawResult)) {
        return $null
    }

    $text = $RawResult.Trim().ToLowerInvariant()
    if ($text -eq '0' -or $text -eq '0x0') {
        return $true
    }

    $asInt = 0
    if ([int]::TryParse($text, [ref]$asInt)) {
        return ($asInt -eq 0)
    }

    if ($text -match '^0x[0-9a-f]+$') {
        try {
            $asHex = [convert]::ToInt64($text.Substring(2), 16)
            return ($asHex -eq 0)
        }
        catch {
            return $null
        }
    }

    return $null
}

Write-Host "=== Pixel7 Holiday Update Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
    Write-Host "--- Latest Output ---" -ForegroundColor Cyan
    Write-Host "latest_ts: N/A" -ForegroundColor Gray
    Write-Host "latest_ok: " -ForegroundColor Gray
    Write-Host "latest_ok_reason: ok_missing" -ForegroundColor Gray
    Write-Host "latest_last_run: N/A" -ForegroundColor Gray
    Write-Host "latest_last_result: " -ForegroundColor Gray
    Write-Host "latest_state: " -ForegroundColor Gray
    Write-Host "latest_next_run: N/A" -ForegroundColor Gray
    exit 1
}

$taskInfo | ForEach-Object { Write-Host $_ }

$taskToRunLine = $taskInfo | Where-Object { $_ -match '^(Task To Run|実行するタスク):\s*' } | Select-Object -First 1
if (-not [string]::IsNullOrWhiteSpace($taskToRunLine)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $taskToRunLine" -ForegroundColor Gray
}

$lastRunLine = $taskInfo | Where-Object { $_ -match '^(Last Run Time|前回の実行時刻):\s*' } | Select-Object -First 1
$lastResultLine = $taskInfo | Where-Object { $_ -match '^(Last Result|前回の結果):\s*' } | Select-Object -First 1
$stateLine = $taskInfo | Where-Object { $_ -match '^(Status|状態):\s*' } | Select-Object -First 1
$nextRunLine = $taskInfo | Where-Object { $_ -match '^(Next Run Time|次回の実行時刻):\s*' } | Select-Object -First 1

$latestLastRun = ''
if (-not [string]::IsNullOrWhiteSpace($lastRunLine)) {
    $latestLastRun = ($lastRunLine -replace '^[^:：]+[:：]\s*','').Trim()
}
if ([string]::IsNullOrWhiteSpace($latestLastRun)) {
    $latestLastRun = 'N/A'
}

$latestLastResult = ''
if (-not [string]::IsNullOrWhiteSpace($lastResultLine)) {
    $latestLastResult = ($lastResultLine -replace '^[^:：]+[:：]\s*','').Trim()
}

$latestState = ''
if (-not [string]::IsNullOrWhiteSpace($stateLine)) {
    $latestState = ($stateLine -replace '^[^:：]+[:：]\s*','').Trim()
}

$latestNextRun = ''
if (-not [string]::IsNullOrWhiteSpace($nextRunLine)) {
    $latestNextRun = ($nextRunLine -replace '^[^:：]+[:：]\s*','').Trim()
}
if ([string]::IsNullOrWhiteSpace($latestNextRun)) {
    $latestNextRun = 'N/A'
}

$latestOk = $null
$latestOkReason = 'result_missing'
if (-not [string]::IsNullOrWhiteSpace($latestLastResult)) {
    $latestOk = Test-TaskResultOk -RawResult $latestLastResult
    if ($null -eq $latestOk) {
        $latestOkReason = 'result_unparseable'
    }
    else {
        $latestOkReason = 'from_last_result'
    }
}

Write-Host "--- Latest Output ---" -ForegroundColor Cyan
Write-Host "latest_ts: $latestLastRun" -ForegroundColor Gray
Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
Write-Host "latest_ok_reason: $latestOkReason" -ForegroundColor Gray
Write-Host "latest_last_run: $latestLastRun" -ForegroundColor Gray
Write-Host "latest_last_result: $latestLastResult" -ForegroundColor Gray
Write-Host "latest_state: $latestState" -ForegroundColor Gray
Write-Host "latest_next_run: $latestNextRun" -ForegroundColor Gray

exit 0
