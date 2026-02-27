param(
    [string]$TaskName = "ManaOS_RLAnything_Bootstrap_Logon",
    [string]$ConfigFile = ""
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\rl_anything_bootstrap_task.config.json"
}

Write-Host "=== RLAnything Bootstrap Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
Write-Host ""

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    throw "Task not found: $TaskName"
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
if (-not [string]::IsNullOrWhiteSpace($latestLastResult)) {
    $latestOk = Test-TaskResultOk -RawResult $latestLastResult
}

Write-Host "--- Latest Output ---" -ForegroundColor Cyan
Write-Host "latest_ts: $latestLastRun" -ForegroundColor Gray
Write-Host "latest_ok: $latestOk" -ForegroundColor Gray
Write-Host "latest_last_run: $latestLastRun" -ForegroundColor Gray
Write-Host "latest_last_result: $latestLastResult" -ForegroundColor Gray
Write-Host "latest_state: $latestState" -ForegroundColor Gray
Write-Host "latest_next_run: $latestNextRun" -ForegroundColor Gray

Write-Host "ConfigFile: $ConfigFile" -ForegroundColor Gray
if (-not (Test-Path $ConfigFile)) {
    Write-Host "[WARN] Config file not found: $ConfigFile" -ForegroundColor Yellow
    exit 0
}

try {
    $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
    Write-Host "--- Config Summary ---" -ForegroundColor Cyan
    Write-Host "task_name: $($cfg.task_name)" -ForegroundColor Gray
    Write-Host "script_path: $($cfg.script_path)" -ForegroundColor Gray
    Write-Host "enable: $($cfg.enable)" -ForegroundColor Gray
    Write-Host "dashboard: $($cfg.dashboard)" -ForegroundColor Gray
}
catch {
    Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
}
